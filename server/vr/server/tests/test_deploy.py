import yaml
from django.utils import timezone

from vr.server.models import App, Build, Release
from vr.server.tasks import build_proc_info
from vr.common.utils import randchars, tmpdir


# If there's a release with current config, and a good build, it should be
# returned by Swarm.get_current_release()

class TestDeploy(object):

    def setup(self):
        self.app = App(name=randchars(), repo_url=randchars(), repo_type='hg')
        self.app.save()

        self.version = 'v1'
        self.build = Build(app=self.app, start_time=timezone.now(),
                           end_time=timezone.now(), tag=self.version,
                           status='success', buildpack_url=randchars(),
                           buildpack_version=randchars(), hash=randchars())
        self.build.file = '%s/build.tar.gz' % randchars()
        self.build.save()

        self.env = {'a': 1}
        self.config = {'b': 2, 'tricky_value': "@We're testing, aren't we?"}
        self.volumes = [['/blah', '/blerg']]
        self.release = Release(build=self.build, env_yaml=self.env,
                               config_yaml=self.config, volumes=self.volumes)
        self.release.save()


    def test_build_proc_info(self):
        info = build_proc_info(self.release, 'test', 'somehost', 'web', 8000)
        assert info['volumes'] == self.volumes

    def test_build_proc_yaml_file(self):
        # Test that the proc.yaml file that gets deployed has the correct
        # information.

        config_name = 'test'
        hostname = 'somehost'
        proc = 'web'
        port = 8000

        with tmpdir():
            # Generate the proc.yaml file the same way that
            # server.vr.server.tasks.deploy() does; then yaml.load() it
            # and compare with the local info.
            with open('proc.yaml', 'w+b') as f:
                info = build_proc_info(self.release, config_name, hostname,
                                       proc, port)
                f.write(yaml.safe_dump(info, default_flow_style=False))

                f.seek(0)
                written_info = yaml.load(f.read())

        assert info == written_info
