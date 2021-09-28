from game_engine.models import Match, User, UserPerformance, UserCode
from game_engine.models import MatchResult
from rest_framework import serializers
import os


class MatchResultSerializer(serializers.HyperlinkedModelSerializer):
    match_events = serializers.SerializerMethodField('load_json')
    match_id = serializers.SerializerMethodField('get_pk')

    @staticmethod
    def load_json(obj):  # makes serializer use actual json instead of string
        return obj.match_events

    @staticmethod
    def get_pk(obj):
        return obj.pk

    class Meta:
        model = MatchResult
        fields = '__all__'


class MatchSerializer(serializers.HyperlinkedModelSerializer):
    game_id = serializers.SerializerMethodField('get_pk')
    players = serializers.SerializerMethodField('get_players')
    decision_timeout = serializers.SerializerMethodField('get_decision_timeout')

    @staticmethod
    def get_players(obj):
        return obj.players

    @staticmethod
    def get_pk(obj):
        return obj.pk

    @staticmethod
    def get_decision_timeout(_):
        timeout = os.environ.get("PLAYER_DECISION_TIMEOUT")
        try:
            timeout = float(timeout)
        except ValueError:
            raise ValueError(f"PLAYER_DECISION_TIMEOUT: {timeout} is not a valid float")
        return timeout

    class Meta:
        model = Match
        fields = ['game_id', 'allocated', 'in_progress', 'players', 'decision_timeout']
#
#
# class MatchResultSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = MatchResult


class UserPerformanceSerializer(serializers.HyperlinkedModelSerializer):
    user_details = serializers.SerializerMethodField('get_user_details')
    pk = serializers.SerializerMethodField('get_pk')

    @staticmethod
    def get_user_details(obj):
        return {'user_pk': obj.user.pk, 'name': obj.user.github_username,
                'year': obj.user.year, 'programme': obj.user.programme}

    @staticmethod
    def get_pk(obj):
        return obj.pk

    class Meta:
        model = UserPerformance
        fields = ['pk', 'url', 'mmr', 'confidence', 'games_played', 'league', 'user', 'user_details']


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email_address', 'github_username', 'student_id']


class UserCodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserCode
        fields = ['user', 'source_code', 'commit_time', 'has_failed']
