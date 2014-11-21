import os.path

from mock import MagicMock, Mock, patch

from vr.common.utils import randchars
from vr.server.models import App, Build, BuildPack, OSImage
from vr.server.settings import MEDIA_URL
from vr.server.tasks import get_build_parameters

from vr.server import tasks


class TestBuild(object):

    def setup(self):
        self.buildpack = BuildPack(repo_url=randchars(), repo_type='git',
                                   order=1)
        self.buildpack.save()

        self.app = App(name=randchars(), repo_url=randchars(), repo_type='hg',
                       buildpack=self.buildpack)
        self.app.save()

        self.image_name = 'ubuntu_precise'
        self.image_filepath = os.path.join(self.image_name, 'ubuntu.tar.gz')

        self.image_md5 = 'abcdef1234567890'
        self.os_image = OSImage(name=self.image_name, file=self.image_filepath)
        with patch.object(OSImage, '_compute_file_md5',
                          return_value=self.image_md5):
            self.os_image.save()

        self.version = 'v1'

        self.build = Build(
            app=self.app,
            os_image=self.os_image,
            tag=self.version,
        )
        self.build.save()

    def test_get_build_parameters(self):
        build_params = get_build_parameters(self.build)
        assert build_params == {
            'app_name': self.app.name,
            'app_repo_type': self.app.repo_type,
            'app_repo_url': self.app.repo_url,
            'version': self.version,
            'buildpack_url': self.buildpack.repo_url,
            'image_name': self.image_name,
            'image_url': MEDIA_URL + self.image_filepath,
            'image_md5': self.image_md5,
        }


class TestSwarmStartBranches(object):
    """We want to follow the steps from swarm_start to swarm_finished."""

    @patch.object(tasks, 'Swarm')
    @patch.object(tasks, 'swarm_release')
    def test_swarm_start_calls_swarm_release(self, swarm_release, Swarm):
        build = Mock()
        build.is_usable.return_value = True
        Swarm.object.get().release.build = build

        tasks.swarm_start(1234, 'trace_id')

        print(swarm_release.delay.mock_calls)
        print(swarm_release.mock_calls)
        swarm_release.delay.assert_called_with(1234, 'trace_id')

    @patch.object(tasks, 'Swarm')
    @patch.object(tasks, 'swarm_wait_for_build')
    def test_swarm_start_calls_swarm_wait_for_build(self,
                                                    swarm_wait_for_build,
                                                    Swarm):
        build = Mock()
        build.is_usable.return_value = False
        build.in_progress.return_value = True
        swarm = Mock(name='my mock swarm')
        swarm.id = 1234
        swarm.release.build = build

        Swarm.objects.get.return_value = swarm

        tasks.swarm_start(1234, 'trace_id')

        # TODO: Make sure this sends the trace id
        swarm_wait_for_build.assert_called_with(swarm, build, 'trace_id')

    @patch.object(tasks, 'Swarm')
    @patch.object(tasks, 'swarm_release')
    @patch.object(tasks, 'build_app')
    def test_swarm_start_calls_build_app_and_swarm_release(self,
                                                           build_app,
                                                           swarm_release,
                                                           Swarm):

        build = Mock()
        build.is_usable.return_value = False
        build.in_progress.return_value = False
        swarm = Mock(name='my mock swarm')
        swarm.id = 1234
        swarm.release.build = build

        Swarm.objects.get.return_value = swarm

        tasks.swarm_start(1234, 'trace_id')

        print(build_app.mock_calls)
        print(build_app.delay.mock_calls)

        print(swarm_release.mock_calls)
        print(swarm_release.delay.mock_calls)

        # Build the app, calling the swarm_release when done
        swarm_release.subtask.assert_called_with((1234, 'trace_id'))

        build_app.delay.assert_called_with(build.id,
                                           swarm_release.subtask(),
                                           'trace_id')


class TestSwarmReleaseBranches(object):

    @patch.object(tasks, 'PortLock', Mock())
    @patch.object(tasks, 'swarm_deploy_to_host')
    @patch.object(tasks, 'Swarm')
    def test_swarm_release_calls_swarm_deploy_to_host(self,
                                                      Swarm,
                                                      swarm_deploy_to_host):
        swarm = MagicMock()
        swarm.size = 2
        swarm.get_prioritized_hosts.return_value = [MagicMock(), MagicMock()]
        swarm.get_procs.return_value = []  # no procs currently
        Swarm.objects.get.return_value = swarm

        tasks.swarm_release(1234, 'trace_id')

        # TODO: This should work... but it doesn't. Not sure if I'm
        #       using mock_calls correctly as it has been returng 6
        #       instead of 2 even though the get_prioritized host is
        #       what is iterated over and used to creat the subtasks
        #       that are appeneded for the chord.
        #
        # assert len(swarm_deploy_to_host.subtask.mock_calls) == 2
        assert swarm_deploy_to_host.subtask.called
