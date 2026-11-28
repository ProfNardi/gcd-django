"""The My Comics list of the issues on sale in a week names its days."""

from runpy import run_path

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import include, path, reverse

from apps.gcd.models import Issue, Publisher, Series
from apps.mycomics import urls as mycomics_urls
from apps.stddata.models import Country, Language

# apps.mycomics.urls has the on-sale list only with MYCOMICS = True.
with override_settings(MYCOMICS=True):
    urlpatterns = run_path(mycomics_urls.__file__)['urlpatterns']
urlpatterns += [path('', include('urls'))]

# ISO week 11 of 2025 runs from Monday 10 March to Sunday 16 March.
WEEK = {'year': 2025, 'week': 11}
DAYS = '2025-03-10 to 2025-03-16'


@pytest.fixture
def week_page(client, db, settings):
    """The page of the week as my.comics.org shows it, with one issue."""
    settings.ROOT_URLCONF = __name__
    settings.MYCOMICS = True
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


def test_sentences_give_the_days_of_the_week(week_page):
    """Both sentences on the count of issues end with the days."""
    assert ('Displaying 1 to 1 of 1 issue on-sale the week %s.' % DAYS
            in week_page)
    assert ('Displaying 1 to 1 of 1 issue on-sale the week from %s.' % DAYS
            in week_page)


def test_page_links_to_the_same_week_on_www(week_page):
    """The page links to the list of the same week on www.comics.org."""
    assert ('<a href="https://www.comics.org%s">Weekly on-sale list at '
            'www.comics.org</a>' % reverse('on_sale_weekly', kwargs=WEEK)
            in week_page)
