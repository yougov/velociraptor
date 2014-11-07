from vr.common.utils import tmpdir, run
from vr.common.tests import tmprepo
from vr.builder.models import BuildPack

def test_version_in_fragment():
    rev = '16c1dba07ee78d5dbee1f965d91d3d61942ccb67'
    url = 'https://github.com/btubbs/vr_python_example.git#' + rev
    with tmpdir():
        bp = BuildPack('bp', url, 'git')
        bp.clone()
        bp.update()
        assert bp.version == rev


def test_buildpack_update_norev():
    with tmprepo('buildpack_hello.tar.gz', 'git', BuildPack) as r:
        rev = 'd0b1df4838d51c694b6bba9b6c3779a5e2a17775'
        # Unlike the Repo superclass, buildpacks can call .update() without
        # passing in a revision, since we don't want to make users think about
        # buildpack versions if they don't have to.
        r.update()
        assert r.version == rev


def test_buildpack_update_rev():
    with tmprepo('buildpack_hello.tar.gz', 'git', BuildPack) as r:
        rev = '410a52780f6fd9d10d09d1da54088c03a0e2933f'
        # But passing in a rev needs to be supported still
        r.update(rev)
        assert r.version == rev

