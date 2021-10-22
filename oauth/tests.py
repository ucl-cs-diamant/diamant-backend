import os
from unittest import mock

import json
import requests
from django.test import TestCase, RequestFactory
from game_engine.models import User

import oauth.utils


# Create your tests here.
class CallbackEndpoint(TestCase):
    def test_missing_code(self):
        response = self.client.get("/api/oauth/callback")
        self.assertEqual(response.status_code, 400)
        # self.assertContains(response, "oauth code missing in callback request")
        # https://doidemandmorecoffee.ams3.digitaloceanspaces.com/2021-09-05T21.54.34.359.39a1539e.png

    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_unsuccessful_exchange(self, patched_exchange):
        patched_exchange.return_value = None

        response = self.client.get("/api/oauth/callback", {"code": "test_code"})
        self.assertEqual(response.status_code, 406)

    @mock.patch('oauth.utils.fetch_github_identity')
    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_successful_exchange_unlinked(self, patched_exchange, patched_gh_ident):
        patched_exchange.return_value = {"Yep": ""}
        patched_gh_ident.return_value = {"login": "ILW8"}

        response = self.client.get("/api/oauth/callback", {"code": "test_code"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logged in as ILW8")
        self.assertContains(response, "redirect")

    @mock.patch('oauth.utils.fetch_github_identity')
    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_successful_exchange_already_linked(self, patched_exchange, patched_gh_ident):
        User.objects.create(student_id=12345678, github_username="ILW8")

        patched_exchange.return_value = {"Yep": ""}
        patched_gh_ident.return_value = {"login": "ILW8"}

        response = self.client.get("/api/oauth/callback", {"code": "test_code"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logged in as ILW8")
        self.assertNotContains(response, "redirect")


class LinkAccountEndpoint(TestCase):
    def test_not_logged_in(self):
        response = self.client.get("/api/oauth/link_account")
        self.assertEqual(response.status_code, 401)

    def test_missing_token(self):
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        response = self.client.get("/api/oauth/link_account")

        self.assertEqual(response.status_code, 400)

    def test_invalid_token(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        response = self.client.get("/api/oauth/link_account", {"token": "no_token_for_you"})

        self.assertEqual(response.status_code, 404)

    def test_already_linked_token(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        User.objects.create(student_id=12345678, github_username="ILW8", authentication_token="this_token_matches")

        response = self.client.get("/api/oauth/link_account", {"token": "this_token_matches"})

        self.assertEqual(response.status_code, 409)

    def test_successfully_linked(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        new_user = User.objects.create(student_id=12345678, authentication_token="this_token_matches")

        response = self.client.get("/api/oauth/link_account", {"token": "this_token_matches"})

        new_user.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(new_user.github_username, "ILW8")


class UtilsTest(TestCase):
    def setUp(self) -> None:
        self.req_factory = RequestFactory()

    #
    # exchange_code_for_token
    @mock.patch('requests.post')
    @mock.patch.dict(os.environ, {'GITHUB_OAUTH_CLIENT_ID': 'not_none', 'GITHUB_OAUTH_CLIENT_SECRET': 'also_not_none'})
    def test_successful_token_exchange(self, mock_post):
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: {}

        mock_post.return_value = response

        exchange_result = oauth.utils.exchange_code_for_token("test_code")
        self.assertEqual(exchange_result, {})

    @mock.patch('requests.post')
    @mock.patch.dict(os.environ, {'GITHUB_OAUTH_CLIENT_ID': 'not_none', 'GITHUB_OAUTH_CLIENT_SECRET': 'also_not_none'})
    def test_bad_code_token_exchange(self, mock_post):
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: {'error': "it didn't work :("}

        mock_post.return_value = response

        exchange_result = oauth.utils.exchange_code_for_token("test_code")
        self.assertIsNone(exchange_result)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_missing_github_config(self):
        exchange_result = oauth.utils.exchange_code_for_token("test_code")
        self.assertIsNone(exchange_result)

    #
    # fetch_github_identity
    @mock.patch('requests.get')
    def test_successful_get_user(self, mock_get):
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: {}

        mock_get.return_value = response

        exchange_result = oauth.utils.fetch_github_identity({"access_token": "test_token"})
        self.assertEqual(exchange_result, {})

    @mock.patch('requests.get')
    def test_bad_token_get_user_200(self, mock_get):
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: {'error': "it didn't work :("}

        mock_get.return_value = response

        exchange_result = oauth.utils.fetch_github_identity({"access_token": "test_token"})
        self.assertIsNone(exchange_result)

    @mock.patch('requests.get')
    def test_bad_token_get_user_not_200(self, mock_get):
        response = requests.Response()
        response.status_code = 401
        response.json = lambda: {'error': "it didn't work :("}

        mock_get.return_value = response

        exchange_result = oauth.utils.fetch_github_identity({"access_token": "test_token"})
        self.assertIsNone(exchange_result)

    #
    # get_token
    def test_token_in_get(self):
        request = self.req_factory.get('/path/does/not/matter', {"token": "good_token"})
        token = oauth.utils.get_token(request)

        self.assertEqual(token, "good_token")

    def test_get_no_token(self):
        request = self.req_factory.get("/")
        token = oauth.utils.get_token(request)
        self.assertEqual(token, None)

    def test_post_token_in_post_query_dict(self):
        request = self.req_factory.post('/path/does/not/matter', {"token": "good_token"})
        token = oauth.utils.get_token(request)

        self.assertEqual(token, "good_token")

    def test_post_token_in_post_body(self):
        request = self.req_factory.post('/path/does/not/matter',
                                        data=json.dumps({"token": "good_token"}),
                                        content_type='application/json')
        token = oauth.utils.get_token(request)

        self.assertEqual(token, "good_token")

    def test_post_no_token(self):
        request = self.req_factory.post("/")
        token = oauth.utils.get_token(request)
        self.assertEqual(token, None)
