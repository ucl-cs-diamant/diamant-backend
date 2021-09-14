from django.db import models
import json
import datetime
import secrets
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from jsonfield import JSONField


def hex_token(n_bytes=16):
    a = secrets.token_hex(nbytes=n_bytes)
    return a


def get_filename(instance, filename):
    return f"{instance.user.id}/" \
           f"{datetime.datetime.now().timestamp()}." \
           f"{filename}"


# Create your models here.
class User(models.Model):
    student_id = models.IntegerField(unique=True)
    email_address = models.CharField(max_length=127, unique=True)
    github_username = models.CharField(max_length=40, unique=True)
    authentication_token = models.CharField(max_length=36, unique=True,
                                            editable=False, default=hex_token)


class UserCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_code = models.FileField(upload_to=get_filename)
    branch = models.CharField(max_length=255)
    to_clone = models.BooleanField(default=False)  # tells us if we want to clone and run this branch

    commit_time = models.DateTimeField()
    commit_sha = models.CharField(max_length=41)

    has_failed = models.BooleanField(default=False)
    is_in_game = models.BooleanField(default=False)


class UserPerformance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mmr = models.DecimalField(max_digits=12, decimal_places=6, default=25.00)
    confidence = models.DecimalField(max_digits=12, decimal_places=7, default=8.33333)
    games_played = models.IntegerField(default=0)
    league = models.IntegerField(default=0)


# takes a list of user IDs
class MatchPlayersField(models.TextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # noinspection PyMethodMayBeStatic
    def from_db_value(self, value, *_):
        if value is None:
            return value
        return json.loads(value)

    def to_python(self, value):
        if not isinstance(value, str) or value is None:
            return value
        return json.loads(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value is None:
            return value
        return json.dumps(value)


class Match(models.Model):
    # allocated = models.BooleanField(default=False)
    allocated = models.DateTimeField(null=True, default=None)
    in_progress = models.BooleanField(default=False)
    over = models.BooleanField(default=False)
    players = MatchPlayersField()

    class Meta:
        verbose_name_plural = _("Matches")


class MatchResult(models.Model):
    players = MatchPlayersField()
    winners = MatchPlayersField()
    match_events = JSONField()
    time_started = models.DateTimeField()
    time_finished = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = _("Match results")
