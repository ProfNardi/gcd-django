# Generated by Django 2.2.20 on 2021-08-11 16:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gcd', '0038_character_appearance'),
        ('oi', '0036_generic_feature_brand_emblem'),
    ]

    operations = [
        migrations.AddField(
            model_name='characternamedetailrevision',
            name='is_official_name',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='StoryCharacterRevision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('committed', models.NullBooleanField(db_index=True, default=None)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_flashback', models.BooleanField(default=False)),
                ('is_origin', models.BooleanField(default=False)),
                ('is_death', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('changeset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='storycharacterrevisions', to='oi.Changeset')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_character_revisions', to='gcd.CharacterNameDetail')),
                ('group', models.ManyToManyField(blank=True, to='gcd.Group')),
                ('previous_revision', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='next_revision', to='oi.StoryCharacterRevision')),
                ('role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gcd.CharacterRole')),
                ('story_character', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='gcd.StoryCharacter')),
                ('story_revision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_character_revisions', to='oi.StoryRevision')),
            ],
            options={
                'db_table': 'oi_story_character_revision',
                'ordering': ['character__sort_name'],
            },
        ),
    ]
