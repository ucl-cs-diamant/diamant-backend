from django.http import JsonResponse
# from django.shortcuts import render
# from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status

from game_engine.models import User
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
# print(a)


# todo: replace these views with DRF views


@require_http_methods(["GET"])
def oauth_code_callback(request):
    code = request.GET.get('code', None)
    if code is None:
        return JsonResponse({'ok': False, 'message': 'oauth code missing in callback request'},
                            status=status.HTTP_400_BAD_REQUEST)

    exchange_result = utils.exchange_code_for_token(code)
    if exchange_result is None:
        return JsonResponse({'ok': False, 'message': 'Unable to exchange code for token, please try again. If the '
                                                     'issue persists, please contact a site administrator'},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

    github_ident = utils.fetch_github_identity(exchange_result)
    request.session['github_username'] = github_ident['login']

    success_response = {'ok': True, 'message': f"Logged in as {github_ident['login']}."}
    if not User.objects.filter(github_username=github_ident['login']).exists():
        success_response['redirect'] = 'oauth/link_account'
    return JsonResponse(success_response)


# @csrf_exempt
@require_http_methods(["GET", "POST"])
def link_account(request):
    if (github_username := request.session.get('github_username', None)) is None:
        return JsonResponse({'ok': False, 'message': "Not logged in, please log in first"},
                            status=status.HTTP_401_UNAUTHORIZED)

    if (link_token := utils.get_token(request)) is None:
        return JsonResponse({'ok': False, 'message': 'Account link token missing'},
                            status=status.HTTP_400_BAD_REQUEST)

    matching_user_qs = User.objects.filter(authentication_token=link_token)
    if not matching_user_qs:
        return JsonResponse({'ok': False, 'message': 'Invalid token'},
                            status=status.HTTP_404_NOT_FOUND)

    token_user = matching_user_qs.first()
    if token_user.github_username:
        return JsonResponse({'ok': False, 'message': f"Student ID {token_user.student_id} already "
                                                     f"linked to {token_user.github_username}"},
                            status=status.HTTP_409_CONFLICT)

    token_user.github_username = github_username
    token_user.save()
    return JsonResponse({'ok': True, 'message': f"Successfully linked student ID {token_user.student_id} "
                                                f"to {github_username}"}, status=status.HTTP_201_CREATED)
