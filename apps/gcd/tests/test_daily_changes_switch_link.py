"""The daily changes page links to the other list of the same day."""

import re

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from apps.indexer.models import Indexer
from apps.stddata.models import Country

SHOW_DATE = '2025-03-14'


@pytest.fixture
def indexer(client, db):
    """A logged-in indexer with imps, to whom the page offers the switch."""
    User.objects.get_or_create(username=settings.ANON_USER_NAME)
    country = Country.objects.get_or_create(
        code='XZY', defaults={'name': 'Test Country'})[0]
    user = User.objects.create_user('some_indexer')
    Indexer.objects.create(user=user, country=country, imps=1)
    client.force_login(user)
    return user


def switch_link(client, url_name):
    """Return the text and the target of the switch link on the page."""
    response = client.get(reverse(url_name, kwargs={'show_date': SHOW_DATE}))
    assert response.status_code == 200
    found = re.search(r'Switch to <a href="([^"]*)">\s*([^<]*?)\s*</a>',
                      response.content.decode())
    assert found, 'the page has no switch link'
    return found.group(2), found.group(1)


def test_all_changes_link_to_my_changes(client, indexer):
    """The page of all changes links to the user's changes of the day."""
    assert switch_link(client, 'changes_by_date') == (
      'my changes',
      reverse('my_changes_by_date', kwargs={'show_date': SHOW_DATE}))


def test_my_changes_link_to_all_changes(client, indexer):
    """The page of the user's changes links to all changes of the day."""
    assert switch_link(client, 'my_changes_by_date') == (
      'all changes',
      reverse('changes_by_date', kwargs={'show_date': SHOW_DATE}))
