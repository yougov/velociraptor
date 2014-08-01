from django.utils import timezone

from vr.server.models import App, Build, Release, Swarm, Squad, release_eq
from vr.common.utils import randchars


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
        self.volumes = [['/foo', '/bar'], ['/baz', '/quux']]

    def test_save_creates_hash(self):
        release = Release(build=self.build, env_yaml=self.env,
                          config_yaml=self.config, volumes=self.volumes)
        release.save()
        assert release.hash  # must not be None or blank.

    def test_release_eq(self):
        r = Release(build=self.build, env_yaml=self.env,
                    config_yaml=self.config, volumes=self.volumes)
        assert release_eq(r, self.config, self.env, self.volumes)

    def test_release_not_eq(self):
        r = Release(build=self.build, env_yaml=self.env,
                    config_yaml=self.config, volumes=self.volumes)
        assert not release_eq(r, {'no': 'match'}, self.env, self.volumes)

    def test_release_eq_empty_config(self):
        r = Release(build=self.build)
        assert release_eq(r, {}, {}, [])

    def test_swarm_reuses_release(self):
        squad = Squad(name=randchars())
        squad.save()

        release = Release(build=self.build, env_yaml=self.env,
                          config_yaml=self.config, volumes=self.volumes)
        release.save()

        swarm = Swarm(
            app=self.app,
            release=release,
            config_name=randchars(),
            proc_name=randchars(),
            squad=squad,
            size=1,
            config_yaml=self.config,
            env_yaml=self.env,
            volumes=self.volumes
        )
        swarm.save()

        assert swarm.get_current_release(self.version) == release

    def test_swarm_creates_release(self):

        # Make an existing release to save with the swarm.
        squad = Squad(name=randchars())
        squad.save()

        release = Release(build=self.build, env_yaml=self.env,
                          config_yaml=self.config, volumes=self.volumes)
        release.save()

        release_count = Release.objects.count()

        swarm = Swarm(
            app=self.app,
            release=release,
            config_name=randchars(),
            proc_name=randchars(),
            squad=squad,
            size=1,
            config_yaml=self.config,
            env_yaml=self.env,
            volumes=self.volumes
        )
        swarm.save()

        # update the swarm with new config.
        swarm.config_yaml = self.config.update({'c': 3})
        swarm.save()

        # get_current_release should make a new release for us from the new
        # config.
        r = swarm.get_current_release(self.version)
        assert Release.objects.count() == release_count + 1
        assert r.id != release.id
