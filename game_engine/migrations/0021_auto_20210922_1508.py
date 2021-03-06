# Generated by Django 3.2.5 on 2021-09-22 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game_engine', '0020_auto_20210914_2330'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='name',
            field=models.CharField(default='', max_length=127),
        ),
        migrations.AddField(
            model_name='user',
            name='programme',
            field=models.CharField(default='', max_length=127),
        ),
        migrations.AddField(
            model_name='user',
            name='year',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='email_address',
            field=models.CharField(max_length=127, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='github_username',
            field=models.CharField(max_length=40, null=True, unique=True),
        ),
    ]
