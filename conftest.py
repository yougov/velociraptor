from vr.tests import dbsetup


def pytest_addoption(parser):
    parser.addoption('--nodb', action='store_true',
            default=False,
            help="Don't destroy/create DB")


def pytest_sessionstart(session):
    if not session.config.option.nodb:
        dbsetup()
