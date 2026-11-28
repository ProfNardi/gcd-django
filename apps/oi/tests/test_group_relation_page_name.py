"""The page that adds a relation to a group names a group relation.

Its heading and its submit button read "Relation with Group", as the
pages that add a relation to a character, feature, story arc or creator
name their own kind of record.
"""
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.gcd.models import Character, Group
from apps.stddata.models import Language

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor(any_indexer):
    """A user with the permission to reserve, which the add pages need."""
    any_indexer.user_permissions.add(Permission.objects.get(
      content_type__app_label='indexer', codename='can_reserve'))
    return any_indexer


@pytest.fixture
def language(db):
    """The language of the test records."""
    return Language.objects.get_or_create(
      code='en', defaults={'name': 'English'})[0]


def _page(client, editor, name, record):
    """Return the text of the add page of the url name for the record."""
    client.force_login(editor)
    response = client.get(reverse(name, args=[record.id]))
    assert response.status_code == 200
    return response.content.decode()


def test_group_relation_page_names_a_group_relation(client, editor,
                                                    language):
    """Heading and button of the group page name a relation with a group."""
    group = Group.objects.create(
      name='Test Team', sort_name='Test Team', description='', notes='',
      year_first_published=1960, language=language)

    page = _page(client, editor, 'add_group_relation', group)

    assert 'Adding Relation with Group' in page
    assert 'Submit New Relation with Group' in page
    assert 'Relation with Character' not in page


def test_character_relation_page_keeps_its_name(client, editor, language):
    """The character page still names a relation with a character."""
    character = Character.objects.create(
      name='Test Hero', sort_name='Test Hero', description='', notes='',
      year_first_published=1960, language=language)

    page = _page(client, editor, 'add_character_relation', character)

    assert 'Adding Relation with Character' in page
    assert 'Submit New Relation with Character' in page
