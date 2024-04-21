# Generated by Django 3.2.11 on 2022-08-01 19:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gcd', '0043_external_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='Universe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('multiverse', models.CharField(db_index=True, max_length=255)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('designation', models.CharField(db_index=True, max_length=255)),
                ('year_first_published', models.IntegerField(db_index=True, null=True)),
                ('year_first_published_uncertain', models.BooleanField(default=False)),
                ('description', models.TextField()),
                ('notes', models.TextField()),
            ],
            options={
                'verbose_name_plural': 'Universes',
                'ordering': ('multiverse', 'designation', 'name'),
            },
        ),
    ]
