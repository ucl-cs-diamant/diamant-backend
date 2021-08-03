import os

import random
import trueskill
from celery import shared_task

from game_engine.models import UserCode, Match, UserPerformance
from django.utils import timezone
# from game_engine.models import UserPerformance


# given a list of players, an index, and number to extract, produce a sublist of the players to participate
def extract_players(player_list, player_index, target_length):
    if player_index >= player_list.count():
        return None
    if target_length > player_list.count():
        return None     # return None if the list given is invalid

    sublist = [player_list[player_index].user.pk]
    offset = 0

    while len(sublist) < target_length:
        offset += 1
        if (player_index - offset) >= 0:    # not out of bounds
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
    return chosen_players


# todo: change from scheduled task to an event driven system
@shared_task
def matchmake(min_game_size: int = 3, target_game_size: int = 4, min_games_in_queue: int = 8):
    current_ready_match_count = Match.objects.filter(allocated=None, in_progress=False, over=False).count()
    if current_ready_match_count < min_games_in_queue:
        matches_to_create = min_games_in_queue - current_ready_match_count
        matches_created = 0
        while matches_created < matches_to_create:
            available_players = UserCode.objects.\
                filter(has_failed=False, is_latest=True, is_in_game=False).select_related('user').only('user', 'is_in_game')
            if available_players.count() < min_game_size:
                return

            # todo: implement performance-based matchmaking
            # players = list(available_players.values_list('user', flat=True).order_by('?')[:target_game_size])
            players = find_players(available_players, target_game_size)
            # players = random.sample(range(available_players.count()),
            #                         min(available_players.count(), target_game_size))
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
