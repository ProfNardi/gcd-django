"""
On www.comics.org the pages of collections and reading lists go to
my.comics.org.
"""
import importlib

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import clear_url_caches, reverse

from apps.gcd.models import Issue, Publisher, Series
from apps.indexer.models import Indexer
from apps.mycomics import urls as mycomics_urls
from apps.mycomics.models import CollectionItem, Collector, \
                                 ConditionGradeScale, ReadingOrder, \
                                 ReadingOrderItem
from apps.stddata.models import Country, Language

# The pages of my.comics.org that www.comics.org routes too.
PAGES = ('view_collection', 'subscriptions_collection', 'view_item',
         'view_reading_order', 'view_reading_order_item')


def _reload_urls():
    """Builds the url patterns again from the current settings."""
    importlib.reload(mycomics_urls)
    importlib.reload(importlib.import_module(settings.ROOT_URLCONF))
    clear_url_caches()


@pytest.fixture
def lists(db):
    """
    A public collection and a public reading list of the same issue, and
    another collector.
    """
    country = Country.objects.get_or_create(
      id=948, defaults={'code': 'w8', 'name': 'Testland W'})[0]
    language = Language.objects.get_or_create(
      id=948, defaults={'code': 'w8', 'name': 'Testish W'})[0]
    series = Series.objects.create(
      name='Some Series', sort_name='Some Series', year_began=1990,
      country=country, language=language, is_comics_publication=True,
      publisher=Publisher.objects.create(
        name='Test Publisher', country=country, year_began=1990),
      publication_dates='1990')
    issue = Issue.objects.create(
      number='1', series=series, sort_code=1, publication_date='1990',
      key_date='1990-01-00')
    scale = ConditionGradeScale.objects.create(name='Some Scale')
    for name in ('owner', 'visitor'):
        user = User.objects.create_user(name)
        Indexer.objects.create(user=user, country=country)
        Collector.objects.create_collector(user, grade_system=scale,
                                           default_language=language)
    collector = User.objects.get(username='owner').collector
    collection = collector.default_have_collection
    collection.public = True
    collection.save()
    CollectionItem.objects.create(issue=issue).collections.add(collection)
    reading_order = ReadingOrder.objects.create(
      collector=collector, name='Some List', public=True)
    ReadingOrderItem.objects.create(reading_order=reading_order,
                                    issue=issue, sequence_number=1)
    return {'collection': collection, 'reading_order': reading_order}


def _path(page, lists):
    """The path of `page` for the collection or the reading list."""
    collection = lists['collection']
    reading_order = lists['reading_order']
    kwargs = {
      'view_collection': {'collection_id': collection.id},
      'subscriptions_collection': {'collection_id': collection.id},
      'view_item': {'collection_id': collection.id,
                    'item_id': collection.items.get().id},
      'view_reading_order': {'reading_order_id': reading_order.id},
      'view_reading_order_item': {'reading_order_id': reading_order.id,
                                  'item_id': reading_order.items.get().id},
    }[page]
    return reverse(page, kwargs=kwargs)


@pytest.mark.parametrize('username', ['owner', 'visitor', None],
                         ids=['owner', 'other collector', 'anonymous'])
@pytest.mark.parametrize('page', PAGES)
def test_page_on_www_goes_to_my_comics(client, lists, page, username):
    """Every visitor gets the same address and query on my.comics.org."""
    if username:
        client.force_login(User.objects.get(username=username))
    path = _path(page, lists) + '?page=2'

    response = client.get(path)

    assert response.status_code == 302
    assert response['Location'] == 'https://my.comics.org' + path


@pytest.mark.parametrize('page', PAGES)
def test_link_of_www_opens_the_page_on_my_comics(client, lists, page):
    """The address that www.comics.org links is the page on my.comics.org."""
    path = _path(page, lists)
    client.force_login(User.objects.get(username='owner'))

    try:
        with override_settings(MYCOMICS=True):
            _reload_urls()
            response = client.get(path)
    finally:
        _reload_urls()

    assert response.status_code == 200
    assert response.resolver_match.url_name == page
