import os
import tempfile
import shutil

import envoy

from raptor import repo
from raptor.util import tmpdir, CommandException


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


def test_hg_update_norev():
    newrev = '13b6ce1e234a'
    oldrev = '496e15fd973f'
    with tmprepo('hg_python_app.tar.gz', 'hg') as r:
        r.update(newrev)
        r.update(oldrev)
        r.update()
        assert os.path.isfile('newfile')


def test_git_update_norev():
    newrev = '6c79fb7d071a9054542114eea70f69d5361a61ff'
    oldrev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmprepo('git_python_app.tar.gz', 'git') as r:
        r.update(newrev)
        r.update(oldrev)
        r.update()
        assert os.path.isfile('newfile')


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
    """Context manager for creating a tmp dir, unpacking a specified repo
    tarball inside it, cd-ing in there, letting you run stuff, and then
    cleaning up and cd-ing back where you were when it's done.
    """
    def __init__(self, tarball, vcs_type):
        # Repo tarballs must be in the same directory as this file.
        here = os.path.dirname(os.path.abspath(__file__))
        self.tarball = os.path.join(here, tarball)
        self.vcs_type = vcs_type
        self.orig_path = os.getcwd()

    def __enter__(self):
        self.temp_path = tempfile.mkdtemp()
        os.chdir(self.temp_path)
        cmd = 'tar -zxf %s --strip-components 1' % self.tarball
        result = envoy.run(cmd)
        if result.status_code != 0:
            raise CommandException(result)
        return repo.Repo('./', vcs_type=self.vcs_type)

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        shutil.rmtree(self.temp_path, ignore_errors=True)
