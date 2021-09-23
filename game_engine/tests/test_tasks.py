import os
from datetime import timedelta

from django.utils import timezone
from django.test import TestCase
from django.core.files import File
import game_engine.models as models
import mock
import game_engine.tasks as tasks
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class TestTasks(TestCase):
    def setUp(self):
        self.user_list = []
        self.user_code_list = []
        self.user_performance_list = []
        self.mock_file = mock.MagicMock(spec=File)
        self.mock_file.name = "testing.py"
        for i in range(4):
            user = models.User.objects.create(
                student_id=i,
                email_address="{name}@ucl.ac.uk".format(name=i),
                github_username="{name}".format(name=i)
            )
            user_code = models.UserCode.objects.create(
                user=user,
                source_code=self.mock_file.name,
                commit_time=timezone.now()
            )
            user_performance = models.UserPerformance.objects.create(
                user=user,
                mmr=25.00 * i,
                confidence=8.33333 - i,
                league=8,
                code=user_code
            )

            self.user_list.append(user)
            self.user_code_list.append(user_code)
            self.user_performance_list.append(user_performance)

        # dummy timeout value since messing around with environment variables is a pain potentially
        self.timeout = float(60)

    def test_match_making_with_players(self):
        tasks.matchmake()
        match = models.Match.objects.all().first()
        self.assertEqual(len(match.players), 4)

        players_in_game_count = models.UserCode.objects.filter(is_in_game=True).count()
        self.assertEqual(players_in_game_count, 4)

    def test_match_making_min_players(self):
        models.UserCode.objects.all().first().delete()
        tasks.matchmake()
        match = models.Match.objects.all().first()
        self.assertEqual(len(match.players), 3)

    def test_match_making_no_players(self):
        for user in self.user_code_list:
            user.delete()
        tasks.matchmake()
        self.assertFalse(models.Match.objects.all().exists())

    def test_match_scrubbing(self):
        tasks.matchmake()
        models.Match.objects.all().update(in_progress=True)
        models.Match.objects.filter(in_progress=True).update(
            allocated=(timezone.now() - timedelta(seconds=self.timeout + 5)))
        tasks.scrub_dead_matches()

        self.assertFalse(models.Match.objects.all().exists())
        self.assertFalse(models.UserCode.objects.filter(is_in_game=True).exists())

    def test_extract_players(self):
        player_list = models.UserPerformance.objects.all().order_by('mmr')

        sublist = tasks.extract_players(player_list, 1, 4)
        self.assertEqual(sublist, list(player_list.values_list('code', flat=True)))

        sublist = tasks.extract_players(player_list, 1, 7)
        self.assertIsNone(sublist)

        sublist = tasks.extract_players(player_list, 8, 7)
        self.assertIsNone(sublist)

        sublist = tasks.extract_players(player_list, 3, 3)
        self.assertEqual(sublist, list(player_list.values_list('code', flat=True)[1:]))

    def test_evaluate_quality(self):
        user_performance = models.UserPerformance.objects.all().order_by('mmr')

        sublist = tasks.extract_players(user_performance, 1, 3)
        quality = tasks.evaluate_quality(user_performance, sublist)
        self.assertEqual(quality, 3.7216736982105365e-05)

    def test_find_players(self):
        user_code = models.UserCode.objects.all()
        player_list, quality = tasks.find_player_codes(user_code, 4)
        self.assertEqual(player_list, list(models.UserCode.objects.values_list('pk', flat=True)))

        player_list, quality = tasks.find_player_codes(user_code, 3)
        self.assertEqual(len(player_list), 3)

    @mock.patch.dict(os.environ, {'MATCH_TIMEOUT': '1'})
    def test_recalculate_leagues(self):
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=10,
            period=IntervalSchedule.SECONDS,
        )

        PeriodicTask.objects.create(
            interval=schedule,
            name='Matchmake',
            task='game_engine.tasks.matchmake',
        )

        tasks.recalculate_leagues()
        player_list = models.UserPerformance.objects.all().order_by('mmr')

        self.assertEqual([1, 2, 4, 8], list(player_list.values_list('league', flat=True)))

    @mock.patch.dict(os.environ, {'MATCH_TIMEOUT': '1'})
    def test_recalculate_leagues_exception(self):
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=10,
            period=IntervalSchedule.SECONDS,
        )

        PeriodicTask.objects.create(
            interval=schedule,
            name='Matchmake',
            task='game_engine.tasks.matchmake',
        )

        tasks.matchmake()
        models.Match.objects.all().update(in_progress=True)

        self.assertRaises(TimeoutError, tasks.recalculate_leagues)

    def test_optimal_quality(self):
        three_players = tasks.find_optimal_quality(3)
        four_players = tasks.find_optimal_quality(4)
        five_players = tasks.find_optimal_quality(5)

        self.assertEqual(0.2000000128000006, three_players)
        self.assertEqual(0.08944272768649317, four_players)
        self.assertEqual(0.04000000512000041, five_players)

    def test_determine_acceptable_match_perfect_quality(self):
        quality = 0.08944272768649317  # optimal quality for four players
        self.assertTrue(tasks.determine_acceptable_match(quality, 4, 0))

    def test_determine_acceptable_match_bad_quality(self):
        quality = 0.0000000001
        self.assertFalse(tasks.determine_acceptable_match(quality, 4, 0))

    def test_determine_acceptable_match_borderline_quality(self):
        quality = 0.087
        self.assertTrue(tasks.determine_acceptable_match(quality, 4, 0))

    def test_determine_acceptable_match_rejects(self):
        quality = 0.08
        self.assertTrue(tasks.determine_acceptable_match(quality, 4, 5))
