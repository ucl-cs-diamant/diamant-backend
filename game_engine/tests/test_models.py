from django.test import TestCase
from django.utils import timezone

import game_engine.models as models


# Create your tests here.


class UserTestCase(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(student_id=28588828,
                                               email_address="hello@ucl.ac.uk",
                                               github_username="hello")

    def test_user_types(self):
        self.assertEqual(type(self.user.student_id), int)
        self.assertEqual(type(self.user.email_address), str)
        self.assertEqual(type(self.user.github_username), str)


class UserPerformanceTestCase(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(student_id=28588828,
                                               email_address="hello@ucl.ac.uk",
                                               github_username="hello")
        self.uc_instance = models.UserCode.objects.create(user=self.user, commit_time=timezone.now())
        self.up_instance = models.UserPerformance.objects.create(user=self.user, code=self.uc_instance)

    def test_up_defaults(self):
        self.assertEqual(self.up_instance.mmr, 25.00)
        self.assertEqual(type(self.up_instance.mmr), float)

        self.assertEqual(self.up_instance.confidence, 8.33333)
        self.assertEqual(type(self.up_instance.confidence), float)

        self.assertEqual(self.up_instance.games_played, 0)
        self.assertEqual(type(self.up_instance.games_played), int)


class MatchTestCase(TestCase):
    def setUp(self):
        self.user = models.User.objects.create(student_id=28588828,
                                               email_address="hello@ucl.ac.uk",
                                               github_username="hello")
        self.match = models.Match.objects.create(players=[self.user.id])

    def test_match_defaults(self):
        self.assertEqual(self.match.allocated, None)
        self.assertFalse(self.match.in_progress)
        self.assertFalse(self.match.over)
        self.assertEqual(self.match.players[0], self.user.id)

# todo: make more in depth tests (negative), and test MatchResult once MatchPlayerField is figured out
