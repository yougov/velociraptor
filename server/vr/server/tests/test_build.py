import tempfile

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.core.files import File

from vr.server import models
from vr.server.tests import randurl
from vr.common.utils import randchars


def test_build_usable():
    app_url = randurl()
    a = models.App(name=randchars(), repo_url=app_url, repo_type='hg')
    a.save()
    with somefile() as f:
        b = models.Build(
            app=a,
            tag='blah',
            start_time=timezone.now() - relativedelta(minutes=2),
            end_time=timezone.now() - relativedelta(minutes=1),
            file=File(f),
            status='success',
        )
        b.save()
    assert b.is_usable() == True


def test_build_unusable_status():
    app_url = randurl()
    a = models.App(name=randchars(), repo_url=app_url, repo_type='hg')
    a.save()
    with somefile() as f:
        b = models.Build(
            app=a,
            tag='blah',
            start_time=timezone.now() - relativedelta(minutes=2),
            end_time=timezone.now() - relativedelta(minutes=1),
            file=File(f),
            status='',
        )
        b.save()
    assert b.is_usable() == False


class somefile():
    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile()
        return self.file

    def __exit__(self, type, value, traceback):
        self.file.close()

