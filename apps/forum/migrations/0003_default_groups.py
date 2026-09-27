from django.db import migrations


def seed_groups(apps, schema_editor):
    Category = apps.get_model("forum", "Category")
    db = schema_editor.connection.alias
    names = ("gcd-main", "gcd-tech", "gcd-policy", "gcd-chat", "gcd-mycomics-users",
             "gcd-canada", "gcd-deutschland", "gcd-france", "gcd-italia",
             "gcd-nederland-vlaanderen", "gcd-norge", "gcd-sverige", "gcd-uk",
             "gcd-editor", "gcd-board", "gcd-error", "gcd-contact")
    for position, name in enumerate(names):
        Category.objects.using(db).get_or_create(slug=name, defaults={
            "name": name, "position": position,
            "is_restricted": name in ("gcd-editor", "gcd-board", "gcd-error", "gcd-contact"),
        })
    root, _ = Category.objects.using(db).get_or_create(slug="gcd", defaults={"name": "GCD", "position": 0})
    for position, (model, name) in enumerate((("issue", "About Issues"), ("series", "About Series"),
                                           ("creator", "About Authors"), ("publisher", "About Publishers"))):
        Category.objects.using(db).get_or_create(slug=f"gcd-about-{model}", defaults={
            "name": name, "parent": root, "entity_model": model, "position": position,
        })


class Migration(migrations.Migration):
    dependencies = [("forum", "0002_group_hierarchy")]
    # Never remove groups or user discussions when rolling back the data step.
    operations = [migrations.RunPython(seed_groups, migrations.RunPython.noop)]
