from django.http import JsonResponse
# from django.shortcuts import render
from . import utils
import urllib.parse


# Create your views here.
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
print(a)


def oauth_code_callback(request):
    code = request.GET.get('code', None)
    if code is None:
        return JsonResponse({'ok': False, 'message': 'Unable to get code from callback request.'})

    exchange_result = utils.exchange_code_for_token(code)
    if exchange_result is None:
        return JsonResponse({'ok': False, 'message': 'Unable to exchange code for token, please try again. If the '
                                                     'issue persists,please contact a site administrator'})

    github_ident = utils.fetch_github_identity(exchange_result)

    return JsonResponse({'ok': True, 'message': github_ident})
