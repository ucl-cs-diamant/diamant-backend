from game_engine.models import Match, User, UserPerformance, UserCode
# from game_engine.models import MatchResult
from rest_framework import serializers


class MatchSerializer(serializers.HyperlinkedModelSerializer):
    game_id = serializers.SerializerMethodField('get_pk')
    players = serializers.SerializerMethodField('get_players')

    @staticmethod
    def get_players(obj):
        return obj.players

    @staticmethod
    def get_pk(obj):
        return obj.pk

    class Meta:
        model = Match
        fields = ['game_id', 'allocated', 'in_progress', 'players']
#
#
# class MatchResultSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = MatchResult


class UserPerformanceSerializer(serializers.HyperlinkedModelSerializer):
    user_name = serializers.SerializerMethodField('get_user_name')

    @staticmethod
    def get_user_name(obj):
        return obj.user.github_username

    class Meta:
        model = UserPerformance
        fields = '__all__'


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email_address', 'github_username', 'student_id']


class UserCodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserCode
        fields = ['user', 'source_code', 'commit_time']
