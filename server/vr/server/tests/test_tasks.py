import os.path

import mock

from vr.common.utils import randchars
from vr.server.models import App, Build, BuildPack, OSImage
from vr.server.settings import MEDIA_URL
from vr.server.tasks import get_build_parameters


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
        with mock.patch.object(OSImage, '_compute_file_md5',
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
