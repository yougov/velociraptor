from django.utils import timezone
import mock

from deployment import models
from project.tests import randchars, randurl


def test_builds_get_current():
    # If you have a build that has the correct tag, and was built from the same
    # buildpack version, then it ought to be reuseable between different
    # swarms.
    app_url = randurl()
    a = models.App(name=randchars(), repo_url=app_url, repo_type='hg')
    a.save()
    now = timezone.now()
    tag = randchars()
    check_mock = lambda x, y: True
    with mock.patch('deployment.models.BuildPack.check_current', check_mock):
        bp_url = randurl()
        bp_version = randchars()
        bp = models.BuildPack(repo_url=bp_url, repo_type='hg', order=0)
        bp.save()

        b = models.Build(app=a,
                  tag=tag,
                  file='abc',
                  start_time=now,
                  end_time=now,
                  status='success',
                  buildpack_url=bp_url,
                  buildpack_version=bp_version,
                 )
        b.save()

        assert models.Build.get_current(a, tag).id == b.id


def test_buildpack_not_current():
    # Builds done with a non-current version of the buildpack should not be
    # reused.
    app_url = randurl()
    a = models.App(name=randchars(), repo_url=app_url, repo_type='hg')
    a.save()
    now = timezone.now()
    tag = randchars()
    check_mock = lambda x, y: False
    with mock.patch('deployment.models.BuildPack.check_current', check_mock):
        bp_url = randurl()
        bp_version = randchars()
        bp = models.BuildPack(repo_url=bp_url, repo_type='hg', order=0)
        bp.save()

        b = models.Build(app=a,
                  tag=tag,
                  file='abc',
                  start_time=now,
                  end_time=now,
                  status='success',
                  buildpack_url=bp_url,
                  buildpack_version=bp_version,
                 )
        b.save()

        assert models.Build.get_current(a, tag) is None
