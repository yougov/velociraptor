import os

import pytest

from vr.common import repo
from vr.common.utils import tmpdir, run
from vr.common.tests import tmprepo


def test_hg_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.hg')
        run('mkdir -p %s' % folder)

        assert repo.guess_folder_vcs(os.getcwd()) == 'hg'


def test_git_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.git')
        run('mkdir -p %s' % folder)

        assert repo.guess_folder_vcs(os.getcwd()) == 'git'


def test_svn_folder_detection():
    with tmpdir():
        folder = os.path.abspath('.svn')
        run('mkdir -p %s' % folder)

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


def test_basename_trailing_space():
    # Catches https://bitbucket.org/yougov/velociraptor/issue/10/
    url = "ssh://hg@bitbucket.org/yougov/velociraptor "
    assert repo.basename(url) == 'velociraptor'
