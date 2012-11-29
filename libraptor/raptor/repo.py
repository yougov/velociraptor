# Tools for doing some simple (clone and pull) operations with repositories.
import os
import urlparse
import re

import vcstools


def guess_url_vcs(url):
    """
    Given a url, try to guess what kind of VCS it's for.  Return None if we
    can't make a good guess.
    """
    parsed = urlparse.urlsplit(url)

    if parsed.scheme in ('git', 'svn'):
        return parsed.scheme
    elif url.endswith('.git'):
        return 'git'
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
        self.vcs = vcstools.VcsClient(vcs_type, folder)

        if url is None and not os.path.isdir(folder):
            raise ValueError('Must provide repo url if folder does not exist')
        url = url or self.vcs.get_url()
        if url.endswith('/'):
            url = url[:-1]
        self.url = url

    def update(self, rev=None):
        # If folder already exists, try updating the repo.  Else do a new
        # checkout
        tip = {
            'git': 'HEAD',
            'hg': 'tip',
            'svn': None,  # not really implemented
        }[self.vcs_type]
        if not os.path.exists(self.folder):
            self.vcs.checkout(self.url)
        # Note: Until
        # https://github.com/tkruse/vcstools/commit/f74273e08966bd45f9f594b3fa0e26668a68ecbf
        # is merged into a release of vcstools, Repo.update() will not force a
        # git fetch to sync the local repo from master.
        self.vcs.update(rev or tip)

    @property
    def basename(self):
        return basename(self.url)

    @property
    def version(self):
        return self.vcs.get_version()

    def __repr__(self):
        values = {'classname': self.__class__.__name__, 'folder':
                  os.path.basename(self.folder)}
        return "%(classname)s <%(folder)s>" % values


def basename(url):
    """
    Return the name of the folder that you'd get if you cloned 'url' into the
    current working directory.
    """
    # Remove trailing slash from url if present
    if url.endswith('/'):
        url = url[:-1]
    # Also strip .git from url if it ends in that.
    return re.sub('\.git$', '', url.split('/')[-1])
