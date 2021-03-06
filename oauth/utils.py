import json
import requests
import os
from typing import Union

import django.http.request
from rest_framework.authentication import BaseAuthentication

from game_engine.models import User


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

    # todo: at this point, we know the user successfully logged in
    # redirect them to the "link account" page to link their github account to student id
    return r.json()


def fetch_github_identity(exchange_result: dict, endpoint='https://api.github.com/user') -> Union[None, dict]:
    headers = {'Authorization': f'token {exchange_result["access_token"]}'}
    r = requests.get(endpoint, headers=headers)
    if r.status_code != 200 or 'error' in r.json():
        return None
    print(r.json())
    return r.json()


def get_token(request):
    link_token = None
    try:
        link_token = request.GET.get('token')
        if request.method == "POST":
            # default checks for request.body instead of request.POST, sometimes data gets put in body
            link_token = request.POST.get('token')
            link_token = json.loads(request.body.decode("utf-8")).get('token') if link_token is None else link_token
        return link_token
    except django.http.request.RawPostDataException:
        return link_token


class CustomSessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        user = request.session.get('github_username', None)
        if user is not None:
            user = User.objects.get(github_username=user)
        return user, None

    def authenticate_header(self, _):
        return "Not logged in, log in."
