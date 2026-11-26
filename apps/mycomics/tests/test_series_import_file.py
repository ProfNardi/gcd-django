"""Import Issues From File on the page of a series."""
import pytest
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.gcd.models import Issue, Publisher, Series
from apps.indexer.models import Indexer
from apps.mycomics.models import Collector, ConditionGradeScale
from apps.stddata.models import Country, Language


@pytest.fixture
def series(db):
    """A series with the issues 1, 2 and 3."""
    country = Country.objects.get_or_create(
      id=949, defaults={'code': 'w9', 'name': 'Testland I'})[0]
    language = Language.objects.get_or_create(
      id=949, defaults={'code': 'w9', 'name': 'Testish I'})[0]
    series = Series.objects.create(
      name='Some Series', sort_name='Some Series', year_began=1990,
      country=country, language=language, is_comics_publication=True,
      publisher=Publisher.objects.create(
        name='Test Publisher', country=country, year_began=1990),
      publication_dates='1990')
    for number in ('1', '2', '3'):
        Issue.objects.create(
          number=number, series=series, sort_code=int(number),
          publication_date='1990', key_date='1990-01-00')
    return series


@pytest.fixture
def collector(series):
    """A logged-in user with the collections every account gets."""
    user = User.objects.create_user('collector')
    Indexer.objects.create(user=user, country=series.country)
    Collector.objects.create_collector(
      user, grade_system=ConditionGradeScale.objects.create(
        name='Some Scale'),
      default_language=series.language)
    return user


def _import(client, series, content):
    """Posts a file of issue numbers as the series page does."""
    return client.post(
      reverse('my_series_issues', kwargs={'series_id': series.id}),
      {'import_issues': 'Import Issues From File',
       'import_my_issues_to_series': SimpleUploadedFile('issues.txt',
                                                        content)})


@pytest.mark.parametrize('line_end', [b'\n', b'\r\n', b'\r'])
def test_import_lists_the_issues_of_the_file(client, series, collector,
                                             line_end):
    """The issues of the numbers in the file are offered for selection."""
    client.force_login(collector)

    response = _import(client, series,
                       line_end.join([b'1', b'#2', b'99', b'']))

    assert response.status_code == 200
    assert {issue.number for issue in response.context['items']} == \
        {'1', '2'}


def test_import_of_unknown_numbers_goes_back_to_the_series(client, series,
                                                           collector):
    """A file without a number of the series leads back with a warning."""
    client.force_login(collector)

    response = _import(client, series, b'99\n')

    assert response.status_code == 302
    assert response['Location'] == reverse(
      'show_series', kwargs={'series_id': series.id})
    assert [str(message) for message in
            get_messages(response.wsgi_request)] == \
        ['no corresponding issues found']
