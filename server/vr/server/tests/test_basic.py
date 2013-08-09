import urlparse

from django.test.client import Client
from django.core.urlresolvers import reverse

from vr.server.tests import get_user


def test_login_required():
    # Try to access the dashboard.  Should get redirected.
    c = Client()
    r = c.get(reverse('dash'))
    assert r.status_code == 302


def test_login():
    u = get_user()
    url = reverse('login')
    c = Client()
    r = c.post(url, data={'username': u.username, 'password': 'password123'})
    # Should be redirected to homepage
    assert urlparse.urlsplit(r['Location']).path == '/'
