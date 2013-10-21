import base64
import json
import unittest

from django.test.client import Client
from django.core.urlresolvers import reverse

from vr.common.utils import randchars
from vr.server.tests import get_user
from vr.server import models


def get_api_url(resource_name, view_name, **kwargs):
    kwargs.update({'resource_name': resource_name, 'api_name': 'v1'})
    return reverse(view_name, kwargs=kwargs)


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


class TestSaveSwarms(unittest.TestCase):
    def setUp(self):
        self.app = models.App(
            name=randchars(),
            repo_url=randchars(),
            repo_type=randchars(), 
            )
        self.app.save()

        self.build = models.Build(
            app=self.app, 
            tag=randchars(),
            file=randchars(),
            status='success',
            hash=randchars(), 
            )
        self.build.save()

        self.release = models.Release(
            build=self.build,
            config_yaml='',
            env_yaml='',
            hash=randchars(),
            )
        self.release.save()

        self.squad=models.Squad(name=randchars())
        self.squad.save()

        # create a swarm object
        self.swarm = models.Swarm(
            app=self.app,
            release=self.release,
            config_name=randchars(),
            proc_name='web',
            squad=self.squad,
        )
        self.swarm.save()

        # Get a logged in client ready
        self.user = get_user()
        self.client = Client()
        self.client.post(reverse('login'), {'username': self.user.username, 'password':'password123'})

    def test_simple_update(self):

        url = get_api_url('swarms', 'api_dispatch_detail', pk=self.swarm.id)
        resp = self.client.get(url)
        doc = json.loads(resp.content)
        assert doc['config_name'] == self.swarm.config_name

        # make a change, PUT it, and assert that it's in the DB.
        doc['config_name'] = 'test_config_name'
        payload = json.dumps(doc)
        resp = self.client.put(url, data=payload, content_type='application/json')

        saved = models.Swarm.objects.get(id=self.swarm.id)
        assert saved.config_name == 'test_config_name'

    def test_update_with_ingredient(self):
        ing = models.ConfigIngredient(
            name=randchars(),
            config_yaml='',
            env_yaml='',
            )
        ing.save()
        self.swarm.config_ingredients.add(ing)

        url = get_api_url('swarms', 'api_dispatch_detail', pk=self.swarm.id)
        resp = self.client.get(url)
        doc = json.loads(resp.content)
        assert doc['config_name'] == self.swarm.config_name

        # make a change, PUT it, and assert that it's in the DB.
        doc['config_name'] = 'test_config_name'
        payload = json.dumps(doc)
        resp = self.client.put(url, data=payload, content_type='application/json')

        saved = models.Swarm.objects.get(id=self.swarm.id)
        assert saved.config_name == 'test_config_name'
