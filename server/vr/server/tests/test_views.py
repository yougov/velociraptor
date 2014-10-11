import unittest

from django.test.client import Client
from django.core.urlresolvers import reverse

from vr.server import models
from vr.common.utils import randchars
from vr.server.tests import get_user
from vr.server.utils import yamlize

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

        url = reverse('edit_swarm', kwargs={'swarm_id':self.swarm.id})
        payload = {
            'app_id': self.swarm.app.id,
            'os_image_id': getattr(self.swarm.release.build.os_image, 'id', ''),
            'squad_id': self.swarm.squad.id,
            'tag': randchars(),
            'config_name': self.swarm.config_name,
            'config_yaml': yamlize(self.swarm.config_yaml),
            'env_yaml': yamlize(self.swarm.env_yaml),
            'volumes': yamlize(self.swarm.volumes),
            'run_as': self.swarm.run_as or 'nobody',
            'mem_limit': self.swarm.mem_limit,
            'memsw_limit': self.swarm.memsw_limit,
            'proc_name': self.swarm.proc_name,
            'size': self.swarm.size,
            'pool': self.swarm.pool or '',
            'balancer': '',
            'config_ingredients': [
                ing.pk for ing in self.swarm.config_ingredients.all()]
        }
        previous_release_id = self.swarm.release_id
        resp = self.client.post(url, data=payload)
        saved = models.Swarm.objects.get(id=self.swarm.id)
        new_release_id = saved.release_id
        assert previous_release_id != new_release_id
