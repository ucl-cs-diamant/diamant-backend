import os

import random
import time

import trueskill
from celery import shared_task
from django.db.models import QuerySet

from game_engine.models import UserCode, Match, UserPerformance
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
import numpy as np

from .utils import Leagues


# given a list of players, an index, and number to extract, produce a sublist of the players to participate
def extract_players(player_list, player_index, target_length):
    if player_index >= player_list.count():
        return None
    if target_length > player_list.count():
        return None  # return None if the list given is invalid

    sublist = [player_list[player_index].user.pk]
    offset = 0

    while len(sublist) < target_length:
        offset += 1
        if (player_index - offset) >= 0:  # not out of bounds
            sublist.insert(0, player_list[player_index - offset].user.pk)

        if (player_index + offset) < player_list.count() and len(sublist) < target_length:
            sublist.append(player_list[player_index + offset].user.pk)
    return sublist


def evaluate_quality(user_performances, player_list):
    chosen_users = user_performances.filter(user__in=player_list)
    env = trueskill.TrueSkill()
    rating_list = []

    for user in chosen_users:
        rating = env.create_rating(float(user.mmr), float(user.confidence))
        rating_list.append([rating])

    return env.quality(rating_list)


def find_players(user_codes, target_size):
    user_performances = UserPerformance.objects.filter(user__in=user_codes.values_list('user')).order_by('mmr')
    random_index = random.randrange(0, user_performances.count())

    chosen_players = extract_players(user_performances, random_index, target_size)
    match_quality = evaluate_quality(user_performances, chosen_players)

    # todo: implement method of retrying if match quality is below a standard/cost function
    return chosen_players, match_quality


def find_optimal_quality(game_size):
    env = trueskill.TrueSkill()
    rating_list = []

    for i in range(game_size):
        rating = env.create_rating(25, 8.333333)
        rating_list.append([rating])

    return env.quality(rating_list)


def determine_acceptable_match(match_quality, game_size, reject_count):
    optimal_q = find_optimal_quality(game_size)

    base_val = 0.1 * optimal_q
    modifier = 0.05 * optimal_q

    tolerance = base_val + (reject_count * modifier)

    return match_quality > (optimal_q - tolerance)
    # if match is acceptable, return True


# todo: change from scheduled task to an event driven system
@shared_task
def matchmake(min_game_size: int = 3, target_game_size: int = 4, min_games_in_queue: int = 8):
    current_ready_match_count = Match.objects.filter(allocated=None, in_progress=False, over=False).count()
    if current_ready_match_count < min_games_in_queue:
        matches_to_create = min_games_in_queue - current_ready_match_count
        matches_created = 0
        while matches_created < matches_to_create:
            available_players = UserCode.objects. \
                filter(has_failed=False, is_in_game=False).select_related('user').only('user')
            if available_players.count() < min_game_size:
                return

            if available_players.count() < target_game_size:
                target_game_size = available_players.count()

            # find initial batch of players, if not acceptable, keep finding more
            players, quality = find_players(available_players, target_game_size)
            rejects = 0
            while not determine_acceptable_match(quality, len(players), rejects):
                players, quality = find_players(available_players, target_game_size)
                rejects += 1

            match = Match()
            match.players = players
            match.save()

            UserCode.objects.filter(user__in=players).update(is_in_game=True)
            matches_created += 1
            print(f"Created match {match.pk} with players {match.players}")


@shared_task
def scrub_dead_matches():
    timeout = os.environ.get("MATCH_TIMEOUT", "60")
    try:
        timeout = float(timeout)
    except ValueError:
        raise ValueError(f"MATCH_TIMEOUT: {timeout} is not a valid float")

    in_progress_matches = Match.objects.filter(in_progress=True)
    for match in in_progress_matches:
        if (timezone.now() - match.allocated).total_seconds() >= timeout:
            print(f"Match {match.pk} dead, removing.")
            players = match.players
            UserCode.objects.filter(user__in=players).update(is_in_game=False)
            match.delete()


def disable_matchmaking():
    timeout = os.environ.get("MATCH_TIMEOUT", "60")
    maximum_wait = 3
    matchmaking_task = PeriodicTask.objects.filter(task="game_engine.tasks.matchmake").first()

    if matchmaking_task is not None:
        matchmaking_task.enabled = False
        matchmaking_task.save()

    wait_count = 0
    while Match.objects.filter(in_progress=True).count() != 0 and wait_count < maximum_wait:
        time.sleep(int(timeout))
        wait_count += 1

        if wait_count == maximum_wait:
            raise TimeoutError("Matches did not complete within timeout")

    return matchmaking_task


def update_league(performances: QuerySet, league):
    for performance in performances:
        performance.league &= 65520  # 65520 = 0b1111 1111 1111 0000
        performance.league |= league
        performance.save()


def update_percentiles(percentile_thresholds):
    for i in range(len(percentile_thresholds) + 1):
        filter_args = {}
        if i > 0:
            filter_args['mmr__gte'] = percentile_thresholds[i - 1]
        if i < len(percentile_thresholds):
            filter_args['mmr__lt'] = percentile_thresholds[i]
        performances = UserPerformance.objects.filter(**filter_args)

        league = Leagues[f"DIV_{i + 1}"].value
        update_league(performances, league)


@shared_task
def recalculate_leagues(percentiles=(25, 50, 75)):
    matchmaking_task = disable_matchmaking()

    all_mmr = np.array(list(map(lambda d: float(d),
                                UserPerformance.objects.all().values_list('mmr', flat=True))))
    thresholds = sorted(map(lambda p: np.percentile(all_mmr, p), percentiles))  # sort lowest->highest
    update_percentiles(thresholds)

    if matchmaking_task is not None:
        matchmaking_task.enabled = True
        matchmaking_task.save()
