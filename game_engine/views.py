from distutils.util import strtobool

from django.core.exceptions import FieldError
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from rest_framework import viewsets
# from rest_framework import authentication
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.routers import APIRootView

from game_engine.models import Match, User, UserCode, MatchResult, UserPerformance, UserSettings
from game_engine.perms import UserLoggedIn, UserLoggedInAndOwnsCode
from game_engine.serializers import UserSerializer, MatchSerializer, UserCodeSerializer, UserPerformanceSerializer, \
    UserSettingsSerializer
from game_engine.serializers import MatchResultSerializer

import random
import os
from trueskill import Rating, rate


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True)
    def user_code_list(self, request, pk=None):
        objects = UserCode.objects.filter(user_id=pk)
        if objects.count() == 0:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        serializer = UserCodeSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def performance_list(self, request, pk=None):
        objects = UserPerformance.objects.filter(user_id=pk, code__primary=True)
        if objects.count() == 0:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        serializer = UserPerformanceSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def user_match_list(self, request, pk=None):
        objects = MatchResult.objects.filter(players__contains=pk).order_by('-time_finished')
        if objects.count() == 0:
            return Response(None, status=status.HTTP_204_NO_CONTENT)

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = MatchResultSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MatchResultSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


# todo: much needed unit tests pls ty
class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def handle_ok_match(request, match):
        if not isinstance(request.data.get("winners", None), list):
            return Response({"ok": False, "message": "No winners provided"}, status=status.HTTP_400_BAD_REQUEST)

        match_players = match.players
        winners = request.data["winners"]

        if not set(winners).issubset(set(match_players)):
            return Response({"ok": False, "message": "One or more winner not part of match"},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(request.data.get("match_history", None), list):
            return Response({"ok": False, "message": "Missing match history"}, status=status.HTTP_400_BAD_REQUEST)

        match_result = MatchResult()
        match_result.time_started = match.allocated
        match_result.players = match.players
        match_result.winners = request.data["winners"]
        match_result.match_events = request.data["match_history"]
        match_result.save()

        match.delete()

        ranks, rating_group = MatchViewSet.prep_for_rating(match_players, winners)

        new_ratings = rate(rating_group, ranks)  # generate new MMRs based on TrueSkill

        for player in match_players:  # update every player with their new MMRs
            up_instance = UserPerformance.objects.get(code__pk=player)
            player_rating = new_ratings.pop(0)[0]  # needs two layers to index -> team -> player
            up_instance.mmr = player_rating.mu
            up_instance.confidence = player_rating.sigma
            up_instance.save()

        UserCode.objects.filter(pk__in=match_players).update(is_in_game=False)
        return Response(status=status.HTTP_201_CREATED)

    @staticmethod
    def prep_for_rating(match_players, winners):
        rating_group = []  # list of player ratings and their win/loss pos
        ranks = []
        for player in match_players:
            player_code_instance = UserCode.objects.get(pk=player)
            up_instance, _ = UserPerformance.objects.get_or_create(code=player_code_instance,
                                                                   user=player_code_instance.user)
            up_instance.games_played += 1
            up_instance.save()

            player_elo = up_instance.mmr  # pull player elo and confidence amounts
            player_confidence = up_instance.confidence

            rating = Rating(float(player_elo), float(player_confidence))
            rating_group.append([rating])
            if player in winners:  # 0 is a winning player
                ranks.append(0)
            else:
                ranks.append(1)
        return ranks, rating_group

    # noinspection PyUnusedLocal,PyShadowingBuiltins
    @action(methods=["POST"], detail=True, permission_classes=[])
    def report_match(self, request, pk=None, format=None):
        try:
            match = Match.objects.get(pk=pk)
        except Match.DoesNotExist:
            return Response({"ok": False, "message": "Match has been timed out"}, status=status.HTTP_410_GONE)

        if "outcome" not in request.data:
            return Response({"ok": False, "message": "No outcome specified"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data["outcome"] == "ok":
            return self.handle_ok_match(request=request, match=match)
        if request.data["outcome"] == "fail":
            if not isinstance(request.data.get("causes", None), list):
                return Response({"ok": False, "message": "Missing failure causes"})
            for player_code, cause in request.data["causes"].items():
                print(player_code, cause)
                if cause in ["timeout", "died"]:
                    pass  # todo: do something if a player times out


class MatchProvider(viewsets.ViewSet):
    @staticmethod
    def list(request):
        available_matches = Match.objects.filter(allocated__isnull=True, in_progress=False, over=False)
        if available_matches.count() > 0:
            match = random.choice(available_matches)
            match.allocated = timezone.now()  # prevents another request from getting the same match
            match.in_progress = True
            match.save()
            serializer = MatchSerializer(match)
            return JsonResponse(serializer.data)
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class UserCodeViewSet(viewsets.ModelViewSet):
    queryset = UserCode.objects.all()
    serializer_class = UserCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, permission_classes=[])
    def download(self, request, pk=None):
        user_code = UserCode.objects.filter(pk=pk).first()
        if user_code is not None:
            resp = HttpResponse(user_code.source_code.file, content_type="application/octet-stream")
            resp['Content-Disposition'] = f'attachment; filename={os.path.basename(user_code.source_code.name)}'
            return resp
        return Response(status=status.HTTP_404_NOT_FOUND)  # this should not happen to the game runner (matchmaking)


class UserPerformanceViewSet(viewsets.ModelViewSet):
    queryset = UserPerformance.objects.all()
    serializer_class = UserPerformanceSerializer

    def list(self, request, **kwargs):
        sort_by = request.query_params.get("sort", "mmr")
        sort_order = "-"
        if request.query_params.get("order", "desc") == "asc":
            sort_order = ""
        qs = f"{sort_order}{sort_by}"

        include_non_primary = request.query_params.get("non_primary", "false")
        try:
            include_non_primary = strtobool(include_non_primary)
        except ValueError:
            include_non_primary = False

        try:
            objects = UserPerformance.objects.all().order_by(qs) if include_non_primary \
                else UserPerformance.objects.filter(code__primary=True).order_by(qs)
        except FieldError:
            return Response({"ok": False, "message": f"Unknown sort field '{sort_by}'"},
                            status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = UserPerformanceSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = UserPerformanceSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)


class MatchResultViewSet(viewsets.ModelViewSet):
    queryset = MatchResult.objects.all()
    serializer_class = MatchResultSerializer
    # permission_classes = [permissions.IsAuthenticated]


class SettingsViewSet(viewsets.ViewSet):
    basename = "settings"

    # authentication_classes = [oauth.utils.CustomSessionAuthentication]
    # permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        api_root_dict = {act.__name__: f"{self.basename}-{act.__name__.replace('_', '-')}" for act in
                         self.get_extra_actions()}

        # noinspection PyProtectedMember
        return APIRootView.as_view(api_root_dict=api_root_dict)(request._request)

    @action(detail=False, methods=['GET', 'POST'], permission_classes=[UserLoggedIn])
    def account_settings(self, request):
        gh_un = request.session.get('github_username')
        user_settings = UserSettings.objects.get(user__github_username=gh_un)

        if request.method == "GET":
            serializer = UserSettingsSerializer(user_settings, context={'request': request})
            return Response(serializer.data)

        if request.method == 'POST':
            serializer = UserSettingsSerializer(user_settings,
                                                data=request.data,
                                                partial=True,
                                                context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def enable_codes(self, request, processed_ids: set = None):
        """
        Enables code instances using incoming request data.

        :param request: incoming DRF request instance
        :param processed_ids: optional parsed_ids set with existing IDs
        :return: 2-tuple: (success, result)
        If successful, data is a set of parsed code IDs. Otherwise, result is a 2-tuple containing (failure message,
        status code)
        """
        if "enabled_codes" not in request.data:
            if processed_ids is not None:  # already set if `primary` was passed to request, in which case no error
                return True, processed_ids
            return False, ("No codes to enable", status.HTTP_400_BAD_REQUEST)
        if type(request.data['enabled_codes']) != list:
            return False, ("enabled_codes not a list", status.HTTP_400_BAD_REQUEST)

        processed_ids = set() if processed_ids is None else processed_ids

        id_queue = set(request.data['enabled_codes']) - processed_ids
        user_codes = UserCode.objects.filter(pk__in=id_queue)
        [self.check_object_permissions(request, code) for code in user_codes]
        user_codes.update(to_clone=True)

        processed_ids = set.union(id_queue, processed_ids)

        return True, processed_ids

    def set_primary_code(self, request, parsed_ids: set = None):
        """
        Sets a code instance as primary
        :param request:
        :param parsed_ids:
        :return:
        """
        parsed_ids = set() if parsed_ids is None else parsed_ids

        if "primary" not in request.data:  # not an error, report as success
            return True, None

        try:
            code = int(request.data['primary'])
            parsed_ids.add(code)

            code = UserCode.objects.get(pk=code)
            self.check_object_permissions(request, code)

            UserCode.objects.filter(user__github_username=request.session.get('github_username'),
                                    primary=True).update(primary=False)
            code.primary = True
            code.to_clone = True
            code.save()

        except (ValueError, TypeError):
            return False, (f"Value '{request.data['primary']}' not an ID", status.HTTP_400_BAD_REQUEST)
        except UserCode.DoesNotExist:
            return False, (f"Code instance {request.data['primary']} does not exist", status.HTTP_400_BAD_REQUEST)

        return True, parsed_ids

    def update_enabled_codes(self, request):
        success, result = self.set_primary_code(request)
        if not success:
            return Response(*result)
        success, result = self.enable_codes(request, processed_ids=result)
        if not success:
            return Response(*result)
        processed_ids: set = result

        user_codes = UserCode.objects.filter(user__github_username=request.session.get('github_username'))
        user_codes.exclude(pk__in=processed_ids).exclude(primary=True).update(to_clone=False)

        enabled_user_codes = user_codes.filter(to_clone=True).values_list('pk', flat=True)
        return Response(f"Enabled UserCode ID{'s' if len(enabled_user_codes) > 1 else ''}: "
                        f"{', '.join([str(uc_id) for uc_id in enabled_user_codes])} ")

    @staticmethod
    def get_codes_settings(request):
        request_user = User.objects.get(github_username=request.session.get('github_username'))
        user_codes = UserCode.objects.filter(user=request_user)
        response_data = {uc.pk: {'branch_name': uc.branch,
                                 'primary': uc.primary,
                                 'enabled': uc.to_clone} for uc in user_codes}
        return Response(response_data)

    @action(detail=False, permission_classes=[UserLoggedInAndOwnsCode], methods=['GET', 'POST'])
    def enabled_codes(self, request):
        if request.method == "POST":
            return self.update_enabled_codes(request)

        return self.get_codes_settings(request)
