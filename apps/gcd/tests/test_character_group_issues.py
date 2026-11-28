# -*- coding: utf-8 -*-
"""The issue lists of a character with a group, for an origin universe."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.gcd.models import Character, Group, Issue, Universe


@pytest.fixture
def sample(db):
    """
    The sample character, which appears with the sample origin universe as
    a member of the sample group, and the issue of that appearance.
    """
    call_command('seed_development_data')
    character = Character.objects.get(name__endswith='Captain Example')
    return {
      'character': character,
      'group': Group.objects.get(name__endswith='Example League'),
      'universe': Universe.objects.get(name__endswith='Main Universe'),
      'issue': Issue.objects.get(
        story__appearing_characters__character__character=character),
    }


def _listed_issues(client, url):
    """The issues in the list of the page at `url`."""
    response = client.get(url)
    assert response.status_code == 200
    return [row.record for row in response.context['table'].rows]


def test_list_for_the_origin_universe_has_the_issue(client, sample):
    """The list with the origin universe of the appearance has its issue."""
    url = reverse('character_origin_universe_issues_group', kwargs={
      'character_id': sample['character'].id,
      'universe_id': sample['universe'].id,
      'group_id': sample['group'].id})

    assert _listed_issues(client, url) == [sample['issue']]


def test_list_for_another_universe_is_empty(client, sample):
    """An appearance with another origin universe is left out."""
    other = Universe.objects.create(
      multiverse='Test Multiverse', name='Other Universe',
      designation='Earth-Other', year_first_published=2024)
    url = reverse('character_origin_universe_issues_group', kwargs={
      'character_id': sample['character'].id,
      'universe_id': other.id,
      'group_id': sample['group'].id})

    assert _listed_issues(client, url) == []
