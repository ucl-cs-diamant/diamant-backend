from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient, APIRequestFactory

import game_engine.views as views
import game_engine.models as models

from decimal import Decimal
from collections import OrderedDict


def create_user(user_id):
    user = models.User.objects.create(student_id=user_id,
                                      email_address="{name}@ucl.ac.uk".format(name=user_id),
                                      github_username="{name}".format(name=user_id))
    user.save()
    return user


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

        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333)
        user_performance.save()
        expected = {'url': f'http://testserver/user_performances/{user_performance.pk}/', 'user_name': '1',
                    'mmr': 25.000000, 'pk': user_performance.pk, 'confidence': 8.3333300, 'games_played': 0,
                    'league': 0, 'user': f'http://testserver/users/{user.pk}/'}

        response = self.client.get(f"/users/{user.pk}/performance_list", follow=True)
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
        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333)
        user_performance.save()

        user2 = create_user(2)
        user_performance2 = models.UserPerformance.objects.create(user=user2,
                                                                  mmr=27.00,
                                                                  confidence=8.33333)
        user_performance2.save()

        request = factory.get('/', {'sort': 'mmr', 'order': 'desc'})
        response = view(request)

        expected = [OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance2.pk}/'), ('user_name', '2'),
             ('pk', user_performance2.pk),
             ('mmr', Decimal('27.000000')), ('confidence', Decimal('8.3333300')),
             ('games_played', 0), ('league', 0), ('user', f'http://testserver/users/{user2.pk}/')]), OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance.pk}/'), ('user_name', '1'),
             ('pk', user_performance.pk),
             ('mmr', Decimal('25.000000')), ('confidence', Decimal('8.3333300')), ('games_played', 0),
             ('league', 0), ('user', f'http://testserver/users/{user.pk}/')])]

        self.assertSequenceEqual(expected, response.data)

    def test_user_performance_view_set_list_asc(self):
        factory = APIRequestFactory()
        view = views.UserPerformanceViewSet.as_view({'get': 'list'}, pagination_class=None)

        user = create_user(1)
        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333)
        user_performance.save()

        user2 = create_user(2)
        user_performance2 = models.UserPerformance.objects.create(user=user2,
                                                                  mmr=27.00,
                                                                  confidence=8.33333)
        user_performance2.save()

        request = factory.get('/', {'sort': 'mmr', 'order': 'asc'})
        response = view(request)

        expected = [OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance.pk}/'), ('user_name', '1'),
             ('pk', user_performance.pk),
             ('mmr', Decimal('25.000000')), ('confidence', Decimal('8.3333300')),
             ('games_played', 0), ('league', 0), ('user', f'http://testserver/users/{user.pk}/')]), OrderedDict(
            [('url', f'http://testserver/user_performances/{user_performance2.pk}/'), ('user_name', '2'),
             ('pk', user_performance2.pk),
             ('mmr', Decimal('27.000000')), ('confidence', Decimal('8.3333300')), ('games_played', 0),
             ('league', 0), ('user', f'http://testserver/users/{user2.pk}/')])]

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

        expected = None

        self.assertEqual(expected, response.data)
        self.assertEqual(204, response.status_code)
