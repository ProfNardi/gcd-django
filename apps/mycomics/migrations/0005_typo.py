# Generated by Django 3.2.11 on 2022-01-16 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mycomics', '0004_housekeeping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='digital_used',
            field=models.BooleanField(default=False, verbose_name='track digital versions'),
        ),
    ]
