# Generated by Django 2.2.12 on 2020-11-12 21:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mycomics', '0003_add_digital'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='collectionitem',
            options={'ordering': ['issue__series__sort_name', 'issue__series__year_began', 'issue__series__id', 'issue__sort_code', 'id']},
        ),
    ]
