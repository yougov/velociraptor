import urlparse

import pytest
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from vr.common.utils import randchars
from vr.server.tests import get_user
from vr.server import models


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


def test_config_ingredient_marshaling():
    ci = models.ConfigIngredient(
        name=randchars(),
        config_yaml='1: integer keys are not allowed in XMLRPC',
        env_yaml=None,
    )
    with pytest.raises(ValidationError):
        ci.save()


def test_release_config_marshaling():
    app = models.App(
        name=randchars(),
        repo_url=randchars(),
        repo_type='git'
    )
    app.save()
    b = models.Build(
        app=app,
        tag=randchars(),
    )
    b.save()
    release = models.Release(
        build=b,
        config_yaml=None,
        # numbers can only be 32 bit in xmlrpc
        env_yaml='FACEBOOK_APP_ID: 1234123412341234'
    )
    with pytest.raises(ValidationError):
        release.save()


def test_swarm_config_marshaling():
    app = models.App(
        name=randchars(),
        repo_url=randchars(),
        repo_type='git'
    )
    app.save()
    b = models.Build(
        app=app,
        tag=randchars(),
    )
    b.save()
    release = models.Release(
        build=b,
    )
    release.save()
    squad = models.Squad(name=randchars())
    swarm = models.Swarm(
        app=app,
        release=release,
        config_name=randchars(),
        proc_name=randchars(),
        squad=squad,
        config_yaml='1: integer key!',
    )
    with pytest.raises(ValidationError):
        swarm.save()
