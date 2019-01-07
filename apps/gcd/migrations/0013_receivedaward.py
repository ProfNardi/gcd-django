# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-24 02:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('gcd', '0012_add_bibliography'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReceivedAward',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('award_name', models.CharField(max_length=255)),
                ('no_award_name', models.BooleanField(default=False)),
                ('award_year', models.PositiveSmallIntegerField(null=True)),
                ('award_year_uncertain', models.BooleanField(default=False)),
                ('notes', models.TextField()),
                ('award', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='gcd.Award')),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('data_source', models.ManyToManyField(to='gcd.DataSource')),
            ],
            options={
                'ordering': ('award_year',),
                'db_table': 'gcd_received_award',
                'verbose_name_plural': 'Received Awards',
            },
        ),
    ]