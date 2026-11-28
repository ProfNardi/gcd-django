"""
The page count of an issue in an issue overview is followed by "page" or
"pages" in the language of the page, as its message file gives the singular
and the plural.
"""
import re
from decimal import Decimal

import polib
import pytest
from django.template.loader import render_to_string
from django.utils import translation

from apps.gcd.models import Issue, Publisher, Series
from apps.stddata.models import Country, Language

TEMPLATE = 'gcd/bits/sortable_issue_overview.html'


@pytest.fixture
def german(settings, tmp_path):
    """The German message file holds test translations of page and pages."""
    catalog = polib.POFile()
    catalog.metadata = {'Content-Type': 'text/plain; charset=UTF-8',
                        'Plural-Forms': 'nplurals=2; plural=(n != 1);'}
    catalog.append(polib.POEntry(msgid='page', msgid_plural='pages',
                                 msgstr_plural={0: 'Seite', 1: 'Seiten'}))
    folder = tmp_path / 'de' / 'LC_MESSAGES'
    folder.mkdir(parents=True)
    catalog.save_as_mofile(str(folder / 'django.mo'))
    settings.LOCALE_PATHS = [str(tmp_path)]


@pytest.fixture
def issue(db):
    """An issue of a test series."""
    country = Country.objects.get_or_create(
      id=943, defaults={'code': 'n7', 'name': 'Testland O'})[0]
    language = Language.objects.get_or_create(
      id=943, defaults={'code': 'n7', 'name': 'Testish O'})[0]
    series = Series.objects.create(
      name='Some Series', sort_name='Some Series', year_began=1990,
      country=country, language=language, is_comics_publication=True,
      publication_dates='1990',
      publisher=Publisher.objects.create(
        name='Test Publisher', country=country, year_began=1990))
    return Issue.objects.create(number='1', series=series, sort_code=1,
                                publication_date='1990',
                                key_date='1990-01-00')


@pytest.mark.parametrize('lang, page_count, shown', [
  ('de', '1', '1 Seite'), ('de', '2', '2 Seiten'), ('de', '0.5', '0.5 Seite'),
  ('de', None, '? Seiten'),
  ('en', '1', '1 page'), ('en', '2', '2 pages'), ('en', '0.5', '0.5 page'),
  ('en', None, '? pages')])
def test_page_count_is_followed_by_its_word(german, issue, settings, lang,
                                            page_count, shown):
    """The word follows the count rounded up, as before, in each language."""
    issue.page_count = page_count and Decimal(page_count)
    # The table column renders the template with the context of the page.
    context = {'record': issue, 'value': issue.id,
               'ICON_SET_SYMBOLIC': settings.ICON_SET_SYMBOLIC}

    with translation.override(lang):
        html = render_to_string(TEMPLATE, context)

    assert re.search(r'(?<![\d.])%s(?!\w)' % re.escape(shown),
                     re.sub(r'\s+', ' ', html))
