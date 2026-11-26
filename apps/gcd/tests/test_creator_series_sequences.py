# -*- coding: utf-8 -*-
"""The list of the sequences of a creator in one series."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.gcd.models import StoryCredit


@pytest.mark.django_db
def test_sequences_of_a_creator_in_a_series(client):
    """The page lists the sequences of the creator in the series."""
    call_command('seed_development_data')
    credit = StoryCredit.objects.get()
    url = reverse('creator_series_sequences', kwargs={
      'creator_id': credit.creator.creator.id,
      'series_id': credit.story.issue.series.id})

    response = client.get(url)

    assert response.status_code == 200
    table = response.context['table']
    assert [row.record for row in table.rows] == [credit.story]
