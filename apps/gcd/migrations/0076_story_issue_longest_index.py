from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Index for the longest_story_id subqueries used by the overview and
    on-sale pages:

        Story.objects.filter(issue_id=OuterRef('pk'), type_id=19,
                             deleted=False, ...)
                     .order_by('-page_count')[:1]

    Without it, MySQL may scan the whole page_count index backwards for
    every outer issue row, which caused the load spike of 2026-11-28.
    """

    dependencies = [
        ('gcd', '0075_merge_feature_names_api_v2'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='story',
            index=models.Index(
                fields=['issue', 'deleted', 'type', 'page_count'],
                name='gcd_story_issue_longest_idx',
            ),
        ),
    ]
