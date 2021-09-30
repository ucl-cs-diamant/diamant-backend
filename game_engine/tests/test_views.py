from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient, APIRequestFactory

import game_engine.views as views
import game_engine.models as models

from decimal import Decimal
from collections import OrderedDict

from game_engine.serializers import UserPerformanceSerializer


def create_user(user_id, year=1, programme="Bsc Computer Science"):
    user = models.User.objects.create(student_id=user_id,
                                      programme=programme,
                                      year=year,
                                      email_address="{name}@ucl.ac.uk".format(name=user_id),
                                      github_username="{name}".format(name=user_id))
    user.save()
    return user


def create_user_code(user_instance, is_primary=True):
    user_code = models.UserCode.objects.create(user=user_instance, commit_time=timezone.now(), primary=is_primary)
    user_code.save()
    return user_code


def create_match_result_entry(user):
    user_match = models.MatchResult.objects.create(players=[user.pk],
                                                   winners=[user.pk],
                                                   match_events=[],
                                                   time_started=timezone.datetime(2021, 8, 7, 18, 48, 40,
                                                                                  tzinfo=timezone.utc),
                                                   time_finished=timezone.datetime(2021, 8, 7, 18, 48, 45,
                                                                                   tzinfo=timezone.utc))
    user_match.save()
    return user_match


class TestViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_viewset = views.UserViewSet()

    def test_empty_performance_list(self):
        response = self.client.get("/users/1/performance_list", follow=True)
        self.assertEqual(response.status_code, 204)

    def test_performance_list(self):
        user = create_user(1)
        user_code = create_user_code(user)

        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333,
                                                                 code=user_code)
        user_performance.save()
        expected = {'url': f'http://testserver/user_performances/{user_performance.pk}/',
                    'user_details': {
                        'user_pk': user.pk,
                        'name': user.github_username,
                        'year': user.year,
                        'programme': user.programme,
                    },
                    'mmr': 25.000000,
                    'pk': user_performance.pk,
                    'confidence': 8.3333300,
                    'games_played': 0,
                    'league': 0,
                    'user': f'http://testserver/users/{user.pk}/'}

        response = self.client.get(f"/users/{user.pk}/performance_list", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0], expected)

    def test_user_match_list_empty(self):
        response = self.client.get("/users/1/user_match_list", follow=True)
        self.assertEqual(response.status_code, 204)

    def test_user_match_list(self):
        user = create_user(1)

        user_match = create_match_result_entry(user)

        expected = [{'match_id': user_match.pk,
                     'url': f'http://testserver/match_history/{user_match.pk}/',
                     'match_events': [],
                     'players': f'[{user.pk}]',
                     'winners': f'[{user.pk}]',
                     'time_started': '2021-08-07T18:48:40Z',
                     'time_finished': '2021-08-07T18:48:45Z'}]

        response = self.client.get(f"/users/{user.pk}/user_match_list/", follow=True)
        self.assertEqual(response.json()['results'], expected)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['next'], None)
        self.assertEqual(response.json()['previous'], None)

    def test_action_no_pagination_1(self):
        user = create_user(1)
        user_match = create_match_result_entry(user)

        factory = APIRequestFactory()
        view = views.UserViewSet.as_view({'get': 'user_match_list'}, pagination_class=None)

        request = factory.get('/')
        response = view(request, pk=user.pk)

        expected = [{'match_id': user_match.pk,
                     'url': f'http://testserver/match_history/{user_match.pk}/',
                     'match_events': [],
                     'players': f'[{user.pk}]',
                     'winners': f'[{user.pk}]',
                     'time_started': '2021-08-07T18:48:40Z',
                     'time_finished': '2021-08-07T18:48:45Z'}]

        self.assertEqual(expected, response.data)

    def test_user_performance_view_set_list_default(self):
        factory = APIRequestFactory()
        view = views.UserPerformanceViewSet.as_view({'get': 'list'}, pagination_class=None)

        user = create_user(1)
        user_code = create_user_code(user)
        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333,
                                                                 code=user_code)
        user_performance.save()

        user2 = create_user(2)
        user_code2 = create_user_code(user2)
        user_performance2 = models.UserPerformance.objects.create(user=user2,
                                                                  mmr=27.00,
                                                                  confidence=8.33333,
                                                                  code=user_code2)
        user_performance2.save()

        request = factory.get('/', {'sort': 'mmr', 'order': 'desc'})
        response = view(request)

        key_order = UserPerformanceSerializer.Meta.fields
        expected = [OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance2.pk}/'), ('user_details',
                                                                                       {'user_pk': user2.pk,
                                                                                        'name': user2.github_username,
                                                                                        'year': user2.year,
                                                                                        'programme': user2.programme}),
             ('pk', user_performance2.pk),
             ('mmr', Decimal('27.000000')), ('confidence', Decimal('8.3333300')),
             ('games_played', 0), ('league', 0), ('user', f'http://testserver/users/{user2.pk}/')]), OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance.pk}/'), ('user_details',
                                                                                      {'user_pk': user.pk,
                                                                                       'name': user.github_username,
                                                                                       'year': user.year,
                                                                                       'programme': user.programme}),
             ('pk', user_performance.pk),
             ('mmr', Decimal('25.000000')), ('confidence', Decimal('8.3333300')), ('games_played', 0),
             ('league', 0), ('user', f'http://testserver/users/{user.pk}/')])]
        expected = [{key: od[key] for key in key_order} for od in expected]

        self.assertSequenceEqual(expected, response.data)

    def test_user_performance_view_set_list_asc(self):
        factory = APIRequestFactory()
        view = views.UserPerformanceViewSet.as_view({'get': 'list'}, pagination_class=None)

        user = create_user(1)
        user_code = create_user_code(user)
        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333,
                                                                 code=user_code)
        user_performance.save()

        user2 = create_user(2)
        user_code2 = create_user_code(user2)
        user_performance2 = models.UserPerformance.objects.create(user=user2,
                                                                  mmr=27.00,
                                                                  confidence=8.33333,
                                                                  code=user_code2)
        user_performance2.save()

        request = factory.get('/', {'sort': 'mmr', 'order': 'asc'})
        response = view(request)

        # expected order:
        key_order = UserPerformanceSerializer.Meta.fields
        expected = [
            OrderedDict(
                [('url', f'http://testserver/user_performances/{user_performance.pk}/'),
                 ('user_details',
                  {'user_pk': user.pk,
                   'name': user.github_username,
                   'year': user.year,
                   'programme': user.programme}),
                 ('pk', user_performance.pk),
                 ('mmr', Decimal('25.000000')),
                 ('confidence', Decimal('8.3333300')),
                 ('games_played', 0),
                 ('league', 0),
                 ('user', f'http://testserver/users/{user.pk}/')]),
            OrderedDict(
                [('url', f'http://testserver/user_performances/{user_performance2.pk}/'),
                 ('user_details',
                  {'user_pk': user2.pk,
                   'name': user2.github_username,
                   'year': user2.year,
                   'programme': user2.programme}),
                 ('pk', user_performance2.pk),
                 ('mmr', Decimal('27.000000')),
                 ('confidence', Decimal('8.3333300')),
                 ('games_played', 0),
                 ('league', 0),
                 ('user', f'http://testserver/users/{user2.pk}/')])
        ]
        expected = [{key: od[key] for key in key_order} for od in expected]

        self.assertEqual(expected, response.data)

    def test_user_performance_view_set_list_field_error(self):
        factory = APIRequestFactory()
        view = views.UserPerformanceViewSet.as_view({'get': 'list'}, pagination_class=None)

        request = factory.get('/', {'sort': 'bad_key'})
        response = view(request)

        expected = {'ok': False, 'message': "Unknown sort field 'bad_key'"}

        self.assertEqual(expected, response.data)
        self.assertEqual(400, response.status_code)

    def test_user_performance_view_set_list_no_content(self):
        factory = APIRequestFactory()
        view = views.UserPerformanceViewSet.as_view({'get': 'list'}, pagination_class=None)

        request = factory.get('/')
        response = view(request)

        expected = []

        self.assertEqual(expected, response.data)
        self.assertEqual(200, response.status_code)


class TestSettingsView(TestCase):
    def setUp(self) -> None:
        self.user = create_user(user_id=1)
        self.user_codes = [models.UserCode.objects.create(user=self.user, commit_time=timezone.now())
                           for _ in range(5)]
        self.user_codes[0].primary = True
        self.user_codes[0].to_clone = True
        self.user_codes[0].save()

        self.user_settings = models.UserSettings.objects.create(user=self.user)

    def test_get_account_settings(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'get': 'account_settings'})

        expected = {'user': f'http://testserver/users/{self.user.pk}/', 'hide_identity': True, 'display_name': None}

        request = factory.get('/')
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, response.data)

    def test_update_account_settings(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'account_settings'})

        self.assertEqual(True, self.user_settings.hide_identity)

        request = factory.post('/', {'hide_identity': False})
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)

        self.user_settings.refresh_from_db()
        self.assertEqual(False, self.user_settings.hide_identity)

    def test_update_account_settings_invalid_data(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'account_settings'})

        self.assertEqual(True, self.user_settings.hide_identity)

        request = factory.post('/', {'hide_identity': "totally a boolean"})
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(400, response.status_code)

        self.user_settings.refresh_from_db()
        self.assertEqual(True, self.user_settings.hide_identity)

    def test_set_primary_code(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        request = factory.post('/', {'primary': self.user_codes[0].pk})
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)
        self.user_codes[1].refresh_from_db()
        self.assertEqual(True, self.user_codes[0].to_clone)
        self.assertEqual(True, self.user_codes[0].primary)

        request = factory.post('/', {'primary': self.user_codes[1].pk})
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)
        self.user_codes[1].refresh_from_db()
        self.assertEqual(True, self.user_codes[1].to_clone)
        self.assertEqual(True, self.user_codes[1].primary)
        self.user_codes[0].refresh_from_db()
        self.assertEqual(False, self.user_codes[0].primary)

    def test_set_primary_code_bad_id_1(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        bad_id = [self.user_codes[1].pk]
        request = factory.post('/', {'primary': bad_id}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(400, response.status_code)
        self.assertEqual(f"Value '{bad_id}' not an ID", response.data)
        self.assertEqual(True, self.user_codes[0].primary)
        self.assertEqual(False, self.user_codes[1].primary)

    def test_set_primary_code_bad_id_2(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        bad_id = 3875423896
        request = factory.post('/', {'primary': bad_id}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(400, response.status_code)
        self.assertEqual(True, self.user_codes[0].primary)
        self.assertEqual(f"Code instance {bad_id} does not exist", response.data)

    def test_set_primary_code_missing_key(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        # need to pass enabled codes, otherwise 400
        request = factory.post('/', {'lol_wrong_key': 'whatever', 'enabled_codes': []}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)
        self.assertEqual(True, self.user_codes[0].primary)

    def test_enable_codes(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        self.assertEqual(False, self.user_codes[3].to_clone)

        request = factory.post('/', {'enabled_codes': [self.user_codes[3].pk]}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(200, response.status_code)
        self.user_codes[3].refresh_from_db()
        self.user_codes[0].refresh_from_db()
        self.assertEqual(True, self.user_codes[3].to_clone)
        self.assertEqual(True, self.user_codes[0].primary)
        self.assertEqual(True, self.user_codes[0].to_clone)

    def test_enable_codes_not_list(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        self.assertEqual(False, self.user_codes[3].to_clone)

        request = factory.post('/', {'enabled_codes': self.user_codes[3].pk}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(400, response.status_code)
        self.user_codes[3].refresh_from_db()
        self.assertEqual(False, self.user_codes[3].to_clone)
        self.assertEqual("enabled_codes not a list", response.data)

    def test_enable_codes_no_codes(self):
        factory = APIRequestFactory()

        view = views.SettingsViewSet.as_view({'post': 'update_enabled_codes'})

        self.assertEqual(False, self.user_codes[3].to_clone)

        request = factory.post('/', {}, format="json")
        request.session = {'github_username': self.user.github_username}
        response = view(request)

        self.assertEqual(400, response.status_code)
        self.assertEqual("No codes to enable", response.data)
