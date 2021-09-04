import os
from typing import Union

import requests
from django.http import JsonResponse
# from django.shortcuts import render

# Create your views here.
import urllib.parse

# see https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
# scopes to use (see https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps )
# scopes:     read:user  user:email
# client id:  b681a270eb0071a810bd

scopes = "read:user user:email"
scopes = urllib.parse.quote(scopes)

# noinspection HttpUrlsUsage
redirect_uri = "http://hopefullyup.compositegrid.com:8727/oauth/callback"
redirect_uri = urllib.parse.quote(redirect_uri)
a = f"https://github.com/login/oauth/authorize?client_id=b681a270eb0071a810bd&scope={scopes}" \
    f"&redirect_uri={redirect_uri}"
# https://github.com/login/oauth/authorize?client_id=b681a270eb0071a810bd&
# scope=read%3Auser%20user%3Aemail&redirect_uri=http://hopefullyup.compositegrid.com:8727/oauth/callback
print(a)


def exchange_code_for_token(code: str, endpoint="https://github.com/login/oauth/access_token") -> Union[None, dict]:
    print(f'token exchange code: {code}')
    client_id = os.environ.get('GITHUB_OAUTH_CLIENT_ID', None)
    client_secret = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', None)
    if client_id is None or client_secret is None:
        return None

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
    }
    headers = {'Accept': 'application/json'}

    r = requests.post(endpoint, headers=headers, data=payload)
    if r.status_code != 200 or 'error' in r.json():
        return None
    return r.json()


def fetch_github_identity(exchange_result: dict, endpoint='https://api.github.com/user') -> Union[None, dict]:
    headers = {'Authorization': f'token {exchange_result["access_token"]}'}
    r = requests.get(endpoint, headers=headers)
    if r.status_code != 200:
        return None
    print(r.json())
    return r.json()


def yep_oauth_callback(request):
    code = request.GET.get('code', None)
    if code is None:
        return JsonResponse({'ok': False, 'message': 'Unable to get code from callback request.'})

    exchange_result = exchange_code_for_token(code)
    if exchange_result is None:
        return JsonResponse({'ok': False, 'message': 'Unable to exchange code for token, please try again. If the '
                                                     'issue persists,please contact a site administrator'})

    github_ident = fetch_github_identity(exchange_result)

    return JsonResponse({'ok': True, 'message': github_ident})
