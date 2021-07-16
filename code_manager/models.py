from django.db import models
from game_engine.models import User

# Create your models here.
class Repository(models.Model):
    name = models.CharField(max_length=120)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
