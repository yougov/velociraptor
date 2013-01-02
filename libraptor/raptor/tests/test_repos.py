import os
import tempfile
import shutil

import pytest
import envoy

from raptor import repo, build
from raptor.utils import tmpdir, CommandException


def test_hg_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.hg')
        envoy.run('mkdir -p %s' % folder)

        assert repo.guess_folder_vcs(os.getcwd()) == 'hg'


def test_git_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.git')
        envoy.run('mkdir -p %s' % folder)

        assert repo.guess_folder_vcs(os.getcwd()) == 'git'


def test_svn_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.svn')
        envoy.run('mkdir -p %s' % folder)

        assert repo.guess_folder_vcs(os.getcwd()) == 'svn'


def test_git_scheme_detection():
    url = 'git://github.com/heroku/heroku-buildpack-python'
    assert repo.guess_url_vcs(url) == 'git'


def test_git_suffix_detection():
    url = 'https://github.com/heroku/heroku-buildpack-python.git'
    assert repo.guess_url_vcs(url) == 'git'


def test_basename():
    url = 'https://github.com/heroku/heroku-buildpack-python.git'
    assert repo.basename(url) == 'heroku-buildpack-python'

def test_basename_fragment():
    url = 'https://github.com/heroku/heroku-buildpack-python.git#123456'
    assert repo.basename(url) == 'heroku-buildpack-python'



# TODO: Run local git/hg servers so we don't have to call out over the network
# during tests.
def test_hg_clone():
    url = 'https://bitbucket.org/btubbs/vr_python_example'
    with tmpdir():
        hgrepo = repo.Repo('hgrepo', url, 'hg')
        hgrepo.clone()
        assert hgrepo.get_url() == url


def test_git_clone():
    url = 'https://github.com/btubbs/vr_python_example.git'
    with tmpdir():
        gitrepo = repo.Repo('gitrepo', url, 'git')
        gitrepo.clone()
        assert gitrepo.get_url() == url


def test_version_in_fragment():
    rev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    url = 'https://github.com/btubbs/vr_python_example.git#' + rev
    with tmpdir():
        bp = build.BuildPack('bp', url, 'git')
        bp.clone()
        bp.update()
        assert bp.version == rev


def test_hg_update():
    newrev = '13b6ce1e234a'
    oldrev = '496e15fd973f'
    with tmprepo('hg_python_app.tar.gz', 'hg') as r:
        r.update(newrev)
        f = 'newfile'
        assert os.path.isfile(f)

        r.update(oldrev)
        assert not os.path.isfile(f)


def test_git_update():
    newrev = '6c79fb7d071a9054542114eea70f69d5361a61ff'
    oldrev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmprepo('git_python_app.tar.gz', 'git') as r:
        r.update(newrev)
        f = 'newfile'
        assert os.path.isfile(f)

        r.update(oldrev)
        assert not os.path.isfile(f)


def test_update_norev():
    with tmprepo('hg_python_app.tar.gz', 'hg') as r:
        # repo.update requires passing a revision
        with pytest.raises(TypeError):
            r.update()


def test_buildpack_update_norev():
    with tmprepo('buildpack_hello.tar.gz', 'git', build.BuildPack) as r:
        rev = 'd0b1df4838d51c694b6bba9b6c3779a5e2a17775'
        # Unlike the Repo superclass, buildpacks can call .update() without
        # passing in a revision, since we don't want to make users think about
        # buildpack versions if they don't have to.
        r.update()
        assert r.version == rev


def test_buildpack_update_rev():
    with tmprepo('buildpack_hello.tar.gz', 'git', build.BuildPack) as r:
        rev = '410a52780f6fd9d10d09d1da54088c03a0e2933f'
        # But passing in a rev needs to be supported still
        r.update(rev)
        assert r.version == rev


def test_hg_get_version():
    rev = '496e15fd973f'
    with tmprepo('hg_python_app.tar.gz', 'hg') as r:
        r.update(rev)
        assert r.version == rev


def test_git_get_version():
    rev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmprepo('git_python_app.tar.gz', 'git') as r:
        r.update(rev)
        assert r.version == rev


class tmprepo(object):
    """
    Context manager for creating a tmp dir, unpacking a specified repo tarball
    inside it, cd-ing in there, letting you run stuff, and then cleaning up and
    cd-ing back where you were when it's done.
    """
    def __init__(self, tarball, vcs_type, repo_class=None):
        # Repo tarballs must be in the same directory as this file.
        here = os.path.dirname(os.path.abspath(__file__))
        self.tarball = os.path.join(here, tarball)
        self.vcs_type = vcs_type
        self.orig_path = os.getcwd()
        self.repo_class = repo_class or repo.Repo

    def __enter__(self):
        self.temp_path = tempfile.mkdtemp()
        os.chdir(self.temp_path)
        cmd = 'tar -zxf %s --strip-components 1' % self.tarball
        result = envoy.run(cmd)
        if result.status_code != 0:
            raise CommandException(result)
        return self.repo_class('./', vcs_type=self.vcs_type)

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        shutil.rmtree(self.temp_path, ignore_errors=True)
