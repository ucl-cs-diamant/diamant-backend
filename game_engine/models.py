from django.db import models
import json
import datetime

# Create your models here.
class User(models.Model):
    email_address = models.CharField(max_length=127)
    github_username = models.CharField(max_length=40)
    student_id = models.IntegerField()

class UserCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_code = models.FileField(upload_to= lambda instance, filename: f"{instance.user.id}/"
                                                                         f"{datetime.datetime.now().timestamp()}."
                                                                         f"{filename}")
    commit_time = models.DateTimeField()

class UserPerformance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mmr = models.DecimalField(max_digits=8, decimal_places=4)
    games_played = models.IntegerField()

class MatchPlayersField(models.TextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    allocated = models.BooleanField(default=False)
    in_progress = models.BooleanField(default=False)
    over = models.BooleanField(default=False)
    players = MatchPlayersField()
