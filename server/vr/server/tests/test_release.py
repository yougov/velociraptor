from django.utils import timezone

from vr.server.models import App, Build, Release, Swarm
from vr.common.utils import randchars

# If there's a release with current config, and a good build, it should be
# returned by Swarm.get_current_release()

class TestCurrentRelease(object):

    def setup(self):
        self.app = App(name=randchars(), repo_url=randchars(), repo_type='hg')
        self.app.save()

        self.version = 'v1'
        self.build = Build(app=self.app, start_time=timezone.now(),
                           end_time=timezone.now(), tag=self.version,
                           status='success', buildpack_url=randchars(),
                           buildpack_version=randchars(), hash=randchars())
        self.build.save()

        self.env = {'a': 1}
        self.config = {'b': 2}
        self.release = Release(build=self.build, env_yaml=self.env,
                               config_yaml=self.config)
        self.release.hash = self.release.compute_hash()

        self.squad = Squad()

        self.swarm = Swarm()



    def test_get_current_release_good_build(self):
        assert True

