import base64

from django.test.client import Client
from django.core.urlresolvers import reverse

from vr.tests import get_user


def get_api_url(resource_name, view_name):
    return reverse(view_name,
                   kwargs={'resource_name': resource_name, 'api_name': 'v1'})


class BasicAuthClient(Client):
    """
    Modified Django test client for conviently doing basic auth.  Pass in
    username and password on init.
    """
    def __init__(self, username, password, *args, **kwargs):
        self.auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + base64.b64encode('%s:%s' %
                                                              (username,
                                                               password)),
        }
        super(BasicAuthClient, self).__init__(*args, **kwargs)

    def get(self, url, *args, **kwargs):
        kwargs.update(self.auth_headers)
        return super(BasicAuthClient, self).get(url, *args, **kwargs)


def test_no_auth_denied():
    c = Client()
    url = get_api_url('hosts', 'api_dispatch_list')
    response = c.get(url)
    assert response.status_code == 401


def test_basic_auth_accepted():
    u = get_user()
    c = BasicAuthClient(u.username, 'password123')
    url = get_api_url('hosts', 'api_dispatch_list')
    response = c.get(url)
    assert response.status_code == 200


def test_basic_auth_bad_password():
    u = get_user()
    c = BasicAuthClient(u.username, 'BADPASSWORD')
    url = get_api_url('hosts', 'api_dispatch_list')
    response = c.get(url)
    assert response.status_code == 401


def test_session_auth_accepted():
    u = get_user()
    c = Client()
    c.post(reverse('login'), {'username': u.username, 'password':
                              'password123'})
    url = get_api_url('hosts', 'api_dispatch_list')
    response = c.get(url)
    assert response.status_code == 200
