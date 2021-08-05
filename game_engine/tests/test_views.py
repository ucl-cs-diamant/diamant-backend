from django.test import TestCase, Client
import game_engine.views as views
import game_engine.models as models
import requests
from rest_framework.test import APIClient


class TestViews(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pk = 1
        self.user_viewset = views.UserViewSet()

    def test_empty_performance_list(self):
        response = self.client.get("/users/1/performance_list", follow=True)
        self.assertEqual(response.status_code, 204)

    def test_performance_list(self):
        user = models.User.objects.create(student_id=self.pk,
                                          email_address="{name}@ucl.ac.uk".format(name=self.pk),
                                          github_username="{name}".format(name=self.pk))
        user.save()

        user_performance = models.UserPerformance.objects.create(user=user,
                                                                 mmr=25.00,
                                                                 confidence=8.33333)
        user_performance.save()
        expected = {'url': 'http://testserver/user_performances/1/', 'user_name': '1', 'mmr': '25.000000',
                    'confidence': '8.3333300', 'games_played': 0, 'user': 'http://testserver/users/1/'}

        response = self.client.get("/users/1/performance_list", follow=True)
        print(response.data)
        self.assertEqual(response.json()[0], expected)
