"""
Functions to support the .slugignore feature.  clean_slug_dir(path) is the
main API.

There are two notable differences from the Heroku implementation:
- Velociraptor will not automatically delete repo folders like
  .git.  It will only delete things specified in .slugignore.
- Velociraptor will delete patterns specified in .slugignore *after*
  compilation is finished. (Heroku deletes before compiling.)

"""

from __future__ import print_function

import os
import shutil
import glob


def is_inside(root, item):
    root = os.path.realpath(root)
    item = os.path.realpath(item)

    relative = os.path.relpath(root, item)

    if relative.startswith(os.pardir + os.sep):
        return False
    else:
        return True


def remove(item):
    """
    Delete item, whether it's a file, a folder, or a folder
    full of other files and folders.
    """
    if os.path.isdir(item):
        shutil.rmtree(item)
    else:
        # Assume it's a file. error if not.
        os.remove(item)


def remove_pattern(root, pat, verbose=True):
    """
    Given a directory, and a pattern of files like "garbage.txt" or
    "*pyc" inside it, remove them.

    Try not to delete the whole OS while you're at it.
    """
    print("removing pattern", root, pat)
    combined = root + pat
    print('combined', combined)
    items = glob.glob(combined)
    print('items', items)
    for item in items:
        print('item', item)
        if is_inside(root, item):
            remove(item)
        elif verbose:
            print("{item} is not inside {root}! Skipping.".format(**vars()))


def get_slugignores(root, fname='.slugignore'):
    """
    Given a root path, read any .slugignore file inside and return a list of
    patterns that should be removed prior to slug compilation.

    Return empty list if file does not exist.
    """
    try:
        with open(os.path.join(root, fname)) as f:
            return [l.rstrip('\n') for l in f]
    except IOError:
        return []


def clean_slug_dir(root):
    """
    Given a path, delete anything specified in .slugignore.
    """
    if not root.endswith('/'):
        root += '/'
    for pattern in get_slugignores(root):
        print("pattern", pattern)
        remove_pattern(root, pattern)
