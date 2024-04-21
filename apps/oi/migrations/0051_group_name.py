# Generated by Django 3.2.24 on 2024-03-15 20:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gcd', '0053_group_name'),
        ('oi', '0050_add_universe_for_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupNameDetailRevision',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('committed', models.BooleanField(db_index=True, default=None, null=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('sort_name', models.CharField(default='', max_length=255)),
                ('is_official_name', models.BooleanField(default=False)),
                ('changeset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groupnamedetailrevisions', to='oi.changeset')),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='name_revisions', to='gcd.group')),
                ('group_name_detail', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='gcd.groupnamedetail')),
                ('group_revision', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group_name_revisions', to='oi.grouprevision')),
                ('previous_revision', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='next_revision', to='oi.groupnamedetailrevision')),
            ],
            options={
                'verbose_name_plural': 'Group Name Detail Revisions',
                'db_table': 'oi_group_name_detail_revision',
                'ordering': ['sort_name'],
            },
        ),
    ]
