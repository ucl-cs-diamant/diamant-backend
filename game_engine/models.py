from django.db import models
import json
import datetime
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from jsonfield import JSONField


# Create your models here.
class User(models.Model):
    student_id = models.IntegerField(unique=True)
    email_address = models.CharField(max_length=127, unique=True)
    github_username = models.CharField(max_length=40, unique=True)


def get_filename(instance, filename):
    return f"{instance.user.id}/" \
           f"{datetime.datetime.now().timestamp()}." \
           f"{filename}"


class UserCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_code = models.FileField(upload_to=get_filename)
    commit_time = models.DateTimeField(unique=True)
    has_failed = models.BooleanField(default=False)
    is_latest = models.BooleanField(default=True)
    is_in_game = models.BooleanField(default=False)


class UserPerformance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mmr = models.DecimalField(max_digits=8, decimal_places=2, default=2500.00)
    games_played = models.IntegerField(default=0)


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
