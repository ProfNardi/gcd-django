"""The My Comics list of a week keeps its heading apart from the chooser."""
import importlib
import re

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import clear_url_caches, reverse

from apps.gcd.models import Issue, Publisher, Series
from apps.mycomics import urls as mycomics_urls
from apps.stddata.models import Country, Language

# ISO week 11 of 2025 runs from Monday 10 March to Sunday 16 March.
WEEK = {'year': 2025, 'week': 11}

# The heading on the left, then the box on the right with the week chooser.
HEADING = (r'<h1 class="item_id search_id"> <div class="left"> Issues </div>'
           r' <div class="right"> <div class="h-8 flex">')


def _reload_urls():
    """Builds the url patterns again from the current settings."""
    importlib.reload(mycomics_urls)
    importlib.reload(importlib.import_module(settings.ROOT_URLCONF))
    clear_url_caches()


@pytest.fixture
def mycomics_site():
    """All the pages of My Comics exist only with MYCOMICS = True."""
    with override_settings(MYCOMICS=True):
        _reload_urls()
        yield
    _reload_urls()


@pytest.fixture
def week_page(db, client, mycomics_site):
    """The page of the week as my.comics.org shows it, with one issue."""
    country = Country.objects.get_or_create(
      code='zz', defaults={'name': 'Test Country'})[0]
    language = Language.objects.get_or_create(
      code='zz', defaults={'name': 'Test Language'})[0]
    publisher = Publisher.objects.create(
      name='Test Publisher', country=country, year_began=2025)
    series = Series.objects.create(
      name='Test Series', sort_name='Test Series', publisher=publisher,
      country=country, language=language, year_began=2025)
    Issue.objects.create(series=series, number='1', sort_code=1,
                         on_sale_date='2025-03-12')
    client.force_login(User.objects.create_user('some_collector'))
    response = client.get(reverse('on_sale_weekly', kwargs=WEEK))
    assert response.status_code == 200
    return ' '.join(response.content.decode().split())


def test_chooser_sits_on_the_right_of_both_headings(week_page):
    """Above and below the list the chooser has its own box on the right."""
    assert len(re.findall(HEADING, week_page)) == 2
