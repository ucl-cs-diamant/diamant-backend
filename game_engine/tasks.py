from celery import shared_task

from game_engine.models import UserCode, Match
# from game_engine.models import UserPerformance


# todo: change from scheduled task to an event driven system
@shared_task
def matchmake(min_game_size: int = 3, target_game_size: int = 4, min_games_in_queue: int = 8):
    current_ready_match_count = Match.objects.filter(allocated=None, in_progress=False, over=False).count()
    if current_ready_match_count < min_games_in_queue:
        matches_to_create = min_games_in_queue - current_ready_match_count
        matches_created = 0
        while matches_created < matches_to_create:
            available_players = UserCode.objects.\
                filter(has_failed=False, is_latest=True, is_in_game=False).only('user', 'is_in_game')
            if available_players.count() < min_game_size:
                return

            # todo: implement performance-based matchmaking
            players = list(available_players.values_list('user', flat=True).order_by('?')[:target_game_size])
            # players = random.sample(range(available_players.count()),
            #                         min(available_players.count(), target_game_size))
            match = Match()
            match.players = players
            match.save()

            UserCode.objects.filter(user__in=players).update(is_in_game=True)
            matches_created += 1


@shared_task
def scrub_dead_matches():
    pass
