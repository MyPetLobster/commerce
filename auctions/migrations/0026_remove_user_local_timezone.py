# Generated by Django 5.0.2 on 2024-03-11 16:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0025_user_balance'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='local_timezone',
        ),
    ]
