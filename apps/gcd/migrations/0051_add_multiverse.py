# Generated by Django 3.2.19 on 2023-10-21 17:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gcd', '0050_storygroup'),
    ]

    operations = [
        migrations.CreateModel(
            name='Multiverse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('mainstream', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='is_mainstream', to='gcd.universe')),
            ],
            options={
                'verbose_name_plural': 'Multiverses',
                'ordering': ('name',),
            },
        ),
        migrations.AddField(
            model_name='universe',
            name='verse',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='gcd.multiverse'),
        ),
    ]