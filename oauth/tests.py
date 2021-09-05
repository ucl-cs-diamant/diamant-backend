from unittest import mock

from django.test import TestCase
from game_engine.models import User


# Create your tests here.
class CallbackEndpoint(TestCase):
    def test_missing_code(self):
        response = self.client.get("/oauth/callback")
        self.assertEqual(response.status_code, 400)
        # self.assertContains(response, "oauth code missing in callback request")
        # https://doidemandmorecoffee.ams3.digitaloceanspaces.com/2021-09-05T21.54.34.359.39a1539e.png

    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_unsuccessful_exchange(self, patched_exchange):
        patched_exchange.return_value = None

        response = self.client.get("/oauth/callback", {"code": "test_code"})
        self.assertEqual(response.status_code, 406)

    @mock.patch('oauth.utils.fetch_github_identity')
    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_successful_exchange_unlinked(self, patched_exchange, patched_gh_ident):
        patched_exchange.return_value = {"Yep": ""}
        patched_gh_ident.return_value = {"login": "ILW8"}

        response = self.client.get("/oauth/callback", {"code": "test_code"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logged in as ILW8")
        self.assertContains(response, "redirect")

    @mock.patch('oauth.utils.fetch_github_identity')
    @mock.patch('oauth.utils.exchange_code_for_token')
    def test_successful_exchange_already_linked(self, patched_exchange, patched_gh_ident):
        User.objects.create(student_id=12345678, github_username="ILW8")

        patched_exchange.return_value = {"Yep": ""}
        patched_gh_ident.return_value = {"login": "ILW8"}

        response = self.client.get("/oauth/callback", {"code": "test_code"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logged in as ILW8")
        self.assertNotContains(response, "redirect")


class LinkAccountEndpoint(TestCase):
    def test_not_logged_in(self):
        response = self.client.get("/oauth/link_account")
        self.assertEqual(response.status_code, 401)

    def test_missing_token(self):
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        response = self.client.get("/oauth/link_account")

        self.assertEqual(response.status_code, 400)

    def test_invalid_token(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        response = self.client.get("/oauth/link_account", {"token": "no_token_for_you"})

        self.assertEqual(response.status_code, 404)

    def test_already_linked_token(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        User.objects.create(student_id=12345678, github_username="ILW8", authentication_token="this_token_matches")

        response = self.client.get("/oauth/link_account", {"token": "this_token_matches"})

        self.assertEqual(response.status_code, 409)

    def test_successfully_linked(self):  # token does not match any user in db
        session = self.client.session
        session['github_username'] = "ILW8"
        session.save()

        new_user = User.objects.create(student_id=12345678, authentication_token="this_token_matches")

        response = self.client.get("/oauth/link_account", {"token": "this_token_matches"})

        new_user.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(new_user.github_username, "ILW8")
