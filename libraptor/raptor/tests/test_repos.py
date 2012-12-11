import os

import envoy

from raptor import repo
from raptor.util import tmpdir


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
    url = 'https://bitbucket.org/btubbs/vr_python_example'
    newrev = '13b6ce1e234a'
    oldrev = '496e15fd973f'
    with tmpdir():
        hgrepo = repo.Repo('hgrepo', url, 'hg')
        hgrepo.clone()
        hgrepo.update(newrev)
        f = os.path.join('hgrepo', 'newfile')
        assert os.path.isfile(f)

        hgrepo.update(oldrev)
        assert not os.path.isfile(f)


def test_git_update():
    url = 'https://github.com/btubbs/vr_python_example.git'
    newrev = '6c79fb7d071a9054542114eea70f69d5361a61ff'
    oldrev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmpdir():
        gitrepo = repo.Repo('gitrepo', url, 'git')
        gitrepo.clone()
        gitrepo.update(newrev)
        f = os.path.join('gitrepo', 'newfile')
        assert os.path.isfile(f)

        gitrepo.update(oldrev)
        assert not os.path.isfile(f)


def test_hg_update_norev():
    url = 'https://bitbucket.org/btubbs/vr_python_example'
    newrev = '13b6ce1e234a'
    oldrev = '496e15fd973f'
    with tmpdir():
        hgrepo = repo.Repo('hgrepo', url, 'hg')
        hgrepo.clone()
        hgrepo.update(newrev)
        f = os.path.join('hgrepo', 'newfile')
        assert os.path.isfile(f)

        hgrepo.update(oldrev)
        assert not os.path.isfile(f)

        hgrepo.update()
        assert os.path.isfile(f)


def test_git_update_norev():
    url = 'https://github.com/btubbs/vr_python_example.git'
    newrev = '6c79fb7d071a9054542114eea70f69d5361a61ff'
    oldrev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmpdir():
        gitrepo = repo.Repo('gitrepo', url, 'git')
        gitrepo.clone()
        gitrepo.update(newrev)
        f = os.path.join('gitrepo', 'newfile')
        assert os.path.isfile(f)

        gitrepo.update(oldrev)
        assert not os.path.isfile(f)

        gitrepo.update()
        assert os.path.isfile(f)


def test_hg_get_version():
    url = 'https://bitbucket.org/btubbs/vr_python_example'
    rev = '496e15fd973f'
    with tmpdir():
        hgrepo = repo.Repo('hgrepo', url, 'hg')
        hgrepo.update(rev)
        assert hgrepo.version == rev


def test_git_get_version():
    url = 'https://github.com/btubbs/vr_python_example.git'
    rev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    with tmpdir():
        gitrepo = repo.Repo('gitrepo', url, 'git')
        gitrepo.update(rev)
        assert gitrepo.version == rev
