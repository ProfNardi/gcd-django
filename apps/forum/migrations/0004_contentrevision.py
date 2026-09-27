from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("forum", "0003_default_groups"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="ContentRevision", fields=[
        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("object_id", models.PositiveBigIntegerField()),
        ("ip_address", models.GenericIPAddressField(null=True, blank=True)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("before", models.JSONField(default=dict)),
        ("after", models.JSONField(default=dict)),
        ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype")),
        ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
    ], options={"ordering": ("-created_at",)})]
