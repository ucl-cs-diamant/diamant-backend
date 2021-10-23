from game_engine.models import Match, User, UserPerformance, UserCode, UserSettings
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

    # todo: replace with built-in 'id' field
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
    id = serializers.ReadOnlyField()

    class Meta:
        model = UserCode
        fields = ['id',
                  'url',
                  'user',
                  'branch',
                  'source_code',
                  'to_clone',
                  'primary',
                  'commit_time',
                  'commit_sha',
                  'has_failed']


class UserSettingsSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.HyperlinkedRelatedField(view_name='user-detail', queryset=User.objects.all())
    display_name_options = serializers.SerializerMethodField()

    @staticmethod
    def get_display_name_options(obj: UserSettings):
        # UserSettings.DisplayNameSettings member names correspond to User model field names.
        # DisplayNameSettings(<key>) returns enum member, can access member name using .name (non-translated version)
        # (see https://docs.djangoproject.com/en/3.2/ref/models/fields/#enumeration-types)
        # using getattr, can dynamically get user instance fields using enum member name
        return {
            str(value): {'option': key, 'value': getattr(obj.user, UserSettings.DisplayNameSettings(key).name.lower())}
            for key, value in UserSettings.DisplayNameSettings.choices
        }

    class Meta:
        model = UserSettings
        fields = ['user', 'hide_identity', 'display_name', 'display_name_options']
