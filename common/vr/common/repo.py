# Tools for doing some simple (clone and pull) operations with repositories.
import os
import urlparse
import re
import logging

import requests
from vr.common.utils import chdir, run


log = logging.getLogger(__name__)


def guess_url_vcs(url):
    """
    Given a url, try to guess what kind of VCS it's for.  Return None if we
    can't make a good guess.
    """
    parsed = urlparse.urlsplit(url)

    if parsed.scheme in ('git', 'svn'):
        return parsed.scheme
    elif parsed.path.endswith('.git'):
        return 'git'
    elif parsed.hostname == 'github.com':
        return 'git'

    # If it's an http url, we can try requesting it and guessing from the
    # contents.
    if parsed.scheme in ('http', 'https'):
        resp = requests.get(url)
        if re.match('basehttp.*python.*', resp.headers.get('server').lower()):
            # It's the mercurial http server
            return 'hg'
    return None


def guess_folder_vcs(folder):
    """
    Given a path for a folder on the local filesystem, see what kind of vcs
    repo it is, if any.
    """
    try:
        contents = os.listdir(folder)
        vcs_folders = ['.git', '.hg', '.svn']
        found = next((x for x in vcs_folders if x in contents), None)
        # Chop off the dot if we got a string back
        return found[1:] if found else None
    except OSError:
        return None


class Repo(object):

    def __init__(self, folder, url=None, vcs_type=None):
        # strip trailing slash from folder if present
        if folder.endswith('/'):
            folder = folder[:-1]

        self.folder = folder

        vcs_type = vcs_type or guess_folder_vcs(folder) or guess_url_vcs(url)
        if vcs_type is None:
            raise ValueError('vcs type not guessable from folder (%s) or URL '
                             '(%s) ' % (folder, url))

        self.vcs_type = vcs_type

        if url is None and not os.path.isdir(folder):
            raise ValueError('Must provide repo url if folder does not exist')
        url = url or self.get_url()
        # Strip off fragment
        url, _, self.fragment = url.partition('#')

        # Strip off trailing slash
        if url.endswith('/'):
            url = url[:-1]
        self.url = url

    def run(self, command):

        r = run(command, verbose=True)
        r.raise_for_status()
        return r

    def get_url(self):
        """
        Assuming that the repo has been cloned locally, get its default
        upstream URL.
        """
        cmd = {
            'hg': 'hg paths default',
            'git': 'git config --local --get remote.origin.url',
        }[self.vcs_type]
        with chdir(self.folder):
            r = self.run(cmd)
        return r.output.replace('\n', '')

    def clone(self):
        log.info('Cloning %s to %s' % (self.url, self.folder))
        cmd = {
            'hg': 'hg clone %s %s' % (self.url, self.folder),
            'git': 'git clone %s %s' % (self.url, self.folder),
        }[self.vcs_type]
        self.run(cmd)

    def update(self, rev):
        # If folder doesn't exist, do a clone.  Else pull and update.
        if not os.path.exists(self.folder):
            self.clone()

        log.info('Updating %s from %s' % (self.folder, self.url))

        with chdir(self.folder):
            if self.vcs_type == 'hg':
                self.run('hg pull %s' % self.url)
                self.run('hg up --clean %s' % rev)
            elif self.vcs_type == 'git':
                # NOTE: We don't need the url for git b/c the pull
                #       didn't prompt for a password.
                # NOTE: Use `git fetch` instead `git pull` to avoid a
                #       merge. Use `--tags` to fetch all available
                #       tags.
                self.run('git fetch --tags')
                self.run('git fetch')
                self.run('git checkout %s' % rev)

    @property
    def basename(self):
        return basename(self.url)

    @property
    def version(self):
        if self.vcs_type == 'hg':
            r = self.run('hg identify -i %s' % self.folder)
            return r.output.rstrip('+\n')
        elif self.vcs_type == 'git':
            with chdir(self.folder):
                r = self.run('git rev-parse HEAD')
            return r.output.rstrip()

    def __repr__(self):
        values = {'classname': self.__class__.__name__,
                  'folder': os.path.basename(self.folder)}
        return "%(classname)s <%(folder)s>" % values


def basename(url):
    """
    Return the name of the folder that you'd get if you cloned 'url' into the
    current working directory.
    """
    # It's easy to accidentally have whitespace on the beginning or end of the
    # url.
    url = url.strip()

    url, sep, fragment = url.partition('#')
    # Remove trailing slash from url if present
    if url.endswith('/'):
        url = url[:-1]
    # Also strip .git from url if it ends in that.
    return re.sub('\.git$', '', url.split('/')[-1])
