# Generated by Django 5.0.2 on 2024-03-20 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0034_alter_listing_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='listing',
            name='date',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
