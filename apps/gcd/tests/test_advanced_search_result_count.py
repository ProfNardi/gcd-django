"""Advanced search uses the same exact count for the guard and paging."""

import re
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.gcd.models import Issue, Publisher, Series
from apps.gcd.views import ResponsePaginator, search
from apps.stddata.models import Country, Language


PROCESS = '/search/advanced/process/'
SERIES = 'Exact Count Fixture'


def request_for(target='issue', **values):
    request = RequestFactory().get(
        PROCESS, dict(target=target, series=SERIES, method='iexact', **values))
    request.user = AnonymousUser()
    return request


@pytest.mark.django_db
def test_advanced_issue_page_uses_only_one_exact_count(client):
    country, _ = Country.objects.get_or_create(
        code='xt', defaults={'name': 'Count fixture country'})
    language, _ = Language.objects.get_or_create(
        code='zzt', defaults={'name': 'Count fixture language'})
    publisher = Publisher.objects.create(
        country=country, name='Count Fixture Publisher', year_began=1991)
    series = Series.objects.create(
        name=SERIES, sort_name=SERIES, year_began=1991,
        publisher=publisher, country=country, language=language)
    Issue.objects.bulk_create([
        Issue(series=series, number=str(i), sort_code=i, deleted=(i == 103))
        for i in range(1, 104)
    ])
    matching = list(Issue.objects.filter(series=series, deleted=False)
                    .order_by('sort_code'))

    # Keep the existing table behavior for an out-of-range request: the
    # header's paginator clamps to page two, while the table falls back
    # to page one. The count reuse does not change either paginator.
    for requested_page, visible, absent in (
        (2, matching[-2:], matching[-3]),
        (99, matching[:100], matching[-1]),
    ):
        with CaptureQueriesContext(connection) as captured:
            response = client.get(PROCESS, {
                'target': 'issue', 'series': SERIES, 'method': 'iexact',
                'sort': 'issue', 'page': requested_page,
            })
        assert response.status_code == 200
        page = response.context['page']
        assert page.number == 2
        assert page.paginator.count == 102
        assert page.paginator.per_page == 100
        assert [row.record.pk for row in response.context['table'].paginated_rows] == [
            issue.pk for issue in visible
        ]
        body = response.content.decode()
        for issue in visible:
            assert f'href="{issue.get_absolute_url()}"' in body
        assert f'href="{absent.get_absolute_url()}"' not in body

        counts = []
        for stat in captured:
            sql = stat['sql'].lower().replace('`', '').replace('"', '')
            if re.match(r'\s*select count\(\*\) from \(select distinct gcd_issue\.id\b',
                        sql):
                counts.append(sql)
        assert len(counts) == 1


def test_paginator_uses_a_known_zero_without_counting():
    class EmptyResults(list):
        def count(self):
            pytest.fail('The paginator should use the known zero count')

    response_paginator = ResponsePaginator(EmptyResults(), known_count=0)
    page = response_paginator.paginate(request_for(page=99))
    assert page.number == 1
    assert page.paginator.count == 0
    assert page.start_index() == page.end_index() == 0


@pytest.mark.parametrize(('target', 'count', 'page_size'), [
    ('issue', 50000, 100),
    ('issue', 50001, None),
    ('cover', 101, 50),
    ('issue_cover', 101, 50),
])
def test_guard_and_cover_page_sizes(monkeypatch, target, count, page_size):
    items = MagicMock()
    items.count.return_value = count
    rendered = HttpResponse('results')
    rejected = HttpResponse('too many')
    render_results = MagicMock(return_value=rendered)
    render_error = MagicMock(return_value=rejected)
    monkeypatch.setattr(search, 'do_advanced_search', lambda req: (items, target))
    monkeypatch.setattr(search, 'generic_sortable_list', render_results)
    monkeypatch.setattr(search, 'render_error', render_error)
    monkeypatch.setattr(search, 'IssuePublisherTable', MagicMock())
    monkeypatch.setattr(search, 'CoverIssuePublisherEditTable', MagicMock())

    response = search.process_advanced(request_for(target))
    items.count.assert_called_once_with()
    if page_size is None:
        assert response is rejected
        assert 'More than 50,000 results' in render_error.call_args.args[1]
        render_results.assert_not_called()
    else:
        assert response is rendered
        render_error.assert_not_called()
        render_results.assert_called_once()
        call = render_results.call_args
        assert call.kwargs['known_count'] == count
        size = call.args[5] if len(call.args) > 5 else call.kwargs.get('per_page', 100)
        assert size == page_size


def test_dedicated_csv_still_skips_the_result_count(monkeypatch):
    items = MagicMock(model=Issue)
    response = HttpResponse('csv')
    render_csv = MagicMock(return_value=response)
    monkeypatch.setattr(search, 'do_advanced_search', lambda req: (items, 'issue'))
    monkeypatch.setattr(search, 'render_to_csv_response', render_csv)

    assert search.process_advanced(request_for(), export_csv=True) is response
    items.count.assert_not_called()
    assert items.values.call_args.args[0] == 'id'
    render_csv.assert_called_once_with(items.values.return_value,
                                       append_datestamp=True)


def test_random_result_still_redirects_before_rendering(monkeypatch):
    items = MagicMock()
    items.count.return_value = 1
    item = items.order_by.return_value.__getitem__.return_value
    item.get_absolute_url.return_value = '/issue/234/'
    render_results = MagicMock()
    monkeypatch.setattr(search, 'do_advanced_search', lambda req: (items, 'issue'))
    monkeypatch.setattr(search, 'generic_sortable_list', render_results)

    response = search.process_advanced(request_for(random_search='on'))
    assert response.status_code == 302
    assert response['Location'] == '/issue/234/'
    render_results.assert_not_called()
