#!/usr/bin/python

import sys

import setuptools

PY3 = sys.version_info >= (3,)

py2_reqs = ['suds==0.4'] if not PY3 else []

params = dict(
    name='vr.common',
    namespace_packages=['vr'],
    version='3.5.6',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=setuptools.find_packages(),
    include_package_data=True,
    url='https://bitbucket.org/yougov/velociraptor',
    install_requires=[
        'isodate>=0.4.4',
        'six',
        'utc',
        'requests',
    ] + py2_reqs,
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)

if __name__ == '__main__':
    setuptools.setup(**params)
