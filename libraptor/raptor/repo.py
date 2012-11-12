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
        self.folder = folder

        vcs_type = vcs_type or guess_folder_vcs(folder) or guess_url_vcs(url)
        if vcs_type is None:
            raise ValueError('vcs type not guessable from folder (%s) or URL '
                             '(%s) ' % (folder, url))

        self.vcs_type = vcs_type
        self.vcs = vcstools.VcsClient(vcs_type, folder)

        if url is None and not os.path.isdir(folder):
            raise ValueError('Must provide repo url if folder does not exist')
        self.url = url or self.vcs.get_url()

    def update(self):
        # If folder already exists, try updating the repo.  Else do a new
        # checkout
        if os.path.exists(self.folder):
            tip = {
                'git': 'HEAD',
                'hg': 'tip',
                'svn': None,
            }[self.vcs_type]
            self.vcs.update(tip)
        else:
            self.vcs.checkout(self.url)

    @property
    def basename(self):
        return basename(self.url)

    def __repr__(self):
        values = {'classname': self.__class__.__name__, 'folder':
                  os.path.basename(self.folder)}
        return "%(classname)s <%(folder)s>" % values


def basename(url):
    """
    Return the name of the folder that you'd get if you cloned 'url' into the
    current working directory.
    """
    return re.sub('\.git$', '', url.split('/')[-1])
