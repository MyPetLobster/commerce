# Generated by Django 5.0.2 on 2024-03-17 00:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0028_user_profile_picture_alter_user_balance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='profile_picture',
            field=models.URLField(blank=True, null=True),
        ),
    ]
