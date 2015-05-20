#!/usr/bin/python

import sys

import setuptools

PY3 = sys.version_info >= (3,)

py2_reqs = ['suds==0.4'] if not PY3 else []

params = dict(
    name='vr.common',
    version='3.18',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    url='https://bitbucket.org/yougov/velociraptor',
    description='Libraries and for deploying with Velociraptor',

    packages=setuptools.find_packages(),
    namespace_packages=['vr'],
    include_package_data=True,

    install_requires=[
        'isodate>=0.4.4',
        'six>=1.4.1',
        'utc',
        'requests',
        'PyYAML>=3.10',
        'sseclient==0.0.8',
    ] + py2_reqs,
)

if __name__ == '__main__':
    setuptools.setup(**params)
