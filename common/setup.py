#!/usr/bin/python

import setuptools

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
        'suds==0.4',
        'utc',
        'requests',
    ],
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)

if __name__ == '__main__':
    setuptools.setup(**params)
