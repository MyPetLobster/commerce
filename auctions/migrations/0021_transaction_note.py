# Generated by Django 5.0.2 on 2024-03-09 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0020_alter_listing_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='note',
            field=models.TextField(blank=True, null=True),
        ),
    ]
