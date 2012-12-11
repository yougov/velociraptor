from raptor.build import add_buildpack, App
from raptor.util import tmpdir


def test_buildpack_detected():
    with tmpdir():
        add_buildpack('https://github.com/heroku/heroku-buildpack-nodejs.git')
        add_buildpack('https://github.com/heroku/heroku-buildpack-python.git')
        app = App('node_app', 'https://bitbucket.org/btubbs/vr_node_example',
                  vcs_type='hg')
        app.update()

        assert app.buildpack.basename == 'heroku-buildpack-nodejs'
