"""
When the database gives up on a lock wait or breaks a deadlock, the user gets
an error page that asks to try again, and the request has saved nothing.
"""
import pytest
from django.core import mail
from django.db import OperationalError
from django.urls import path

from apps.indexer.models import Error
from urls import urlpatterns as site_patterns

KEY = 'written by the failed request'
MESSAGE = ('An error occurred when processing the request. Please check and '
           'try again.')


def _failing_view(request, code):
    """Write a row, then fail as the database would."""
    Error.objects.create(error_key=KEY, is_safe=False, error_text='text')
    raise OperationalError(code, 'from the test')


urlpatterns = [path('failing/<int:code>/', _failing_view)] + site_patterns


@pytest.mark.django_db
@pytest.mark.urls(__name__)
@pytest.mark.parametrize('code', [1205, 1213])
def test_a_lock_conflict_gets_a_page(client, caplog, code):
    """
    A lock conflict gives the page with status 503, saves nothing and is
    logged once, by Django as the error that a 5xx answer is, with the
    database error and its traceback.
    """
    response = client.get('/failing/%d/' % code)

    assert response.status_code == 503
    assert MESSAGE in response.content.decode()
    assert not Error.objects.filter(error_key=KEY).exists()
    records = [record for record in caplog.records
               if record.levelname in ('WARNING', 'ERROR')]
    assert [(record.name, record.levelname) for record in records] == [
      ('django.request', 'ERROR')]
    assert records[0].getMessage() == (
      'Service Unavailable: /failing/%d/' % code)
    assert records[0].exc_info[1].args[0] == code


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_the_admins_mail_has_the_lock_conflict(client):
    """
    The one mail to the admins names the database error and has its
    traceback, as the mail of the server error had.
    """
    client.get('/failing/1205/')

    assert len(mail.outbox) == 1
    assert 'Service Unavailable: /failing/1205/' in mail.outbox[0].subject
    body = mail.outbox[0].body
    assert ("OperationalError at /failing/1205/\n(1205, 'from the test')"
            in body)
    assert 'in _failing_view' in body


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_another_database_error_stays_an_error(client):
    """Any other database error reaches the usual error handling."""
    with pytest.raises(OperationalError):
        client.get('/failing/2006/')
