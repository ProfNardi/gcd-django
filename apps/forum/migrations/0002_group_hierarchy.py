from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("forum", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField("category", "parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="forum.category")),
        migrations.AddField("category", "is_restricted", models.BooleanField(default=False)),
        migrations.AddField("category", "members", models.ManyToManyField(blank=True, related_name="forum_groups", to=settings.AUTH_USER_MODEL)),
        migrations.AddField("category", "entity_model", models.CharField(blank=True, max_length=30, choices=[("issue", "Issues"), ("series", "Series"), ("creator", "Authors"), ("publisher", "Publishers")])),
        migrations.AddField("category", "content_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype")),
        migrations.AddField("category", "object_id", models.PositiveBigIntegerField(blank=True, null=True)),
        migrations.AddConstraint("category", models.CheckConstraint(condition=models.Q(content_type__isnull=True, object_id__isnull=True) | models.Q(content_type__isnull=False, object_id__isnull=False), name="forum_category_link_complete")),
        migrations.AddConstraint("category", models.UniqueConstraint(fields=("parent", "content_type", "object_id"), name="forum_category_entity_unique")),
    ]
