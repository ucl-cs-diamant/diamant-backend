from game_engine.models import Match, User, UserPerformance, UserCode
from rest_framework import serializers


class MatchSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Match
        fields = ['id', 'in_progress', 'players']

class UserPerformanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserPerformance
        fields = ['user', 'mmr', 'games_played']

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email_address', 'github_username', 'student_id']

class UserCodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserCode
        fields = ['user', 'source_code', 'commit_time']

