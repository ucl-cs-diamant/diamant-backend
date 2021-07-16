from django.http import HttpResponse

from game_engine.models import Match, User, UserCode
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action


from game_engine.serializers import UserSerializer, MatchSerializer, UserCodeSerializer

import random
import os


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True)
    def user_code_list(self, request, pk=None):
        objects = UserCode.objects.filter(user_id=pk)
        serializer = UserCodeSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def latest_code(self, request, pk=None):
        user_code = UserCode.objects.filter(user=pk)
        if user_code.exists():
            latest_code = user_code.latest("commit_time")
            resp = HttpResponse(latest_code.source_code.file, content_type="application/octet-stream")
            resp['Content-Disposition'] = f'attachment; filename={os.path.basename(latest_code.source_code.name)}'
            return resp
        return Response(status=status.HTTP_404_NOT_FOUND)  # this should not happen to the game runner (matchmaking)


class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]


class MatchProvider(viewsets.ViewSet):
    # noinspection PyMethodMayBeStatic
    def list(self, request):
        available_matches = Match.objects.filter(allocated=False, in_progress=False, over=False)
        if available_matches.count() > 0:
            match = random.choice(available_matches)
            match.allocated = True  # prevents another request to this same endpoint from returning the same match
            match.save()
            serializer = MatchSerializer(match)
            return Response(serializer.data)
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class UserCodeViewSet(viewsets.ModelViewSet):
    queryset = UserCode.objects.all()
    serializer_class = UserCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
