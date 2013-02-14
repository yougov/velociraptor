#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='raptor',
    version='2.11',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Fabric==1.4.0',
        'paramiko>=1.8.0,<2.0',
        'envoy==0.0.2',
        'suds==0.4',
        'supervisor==3.0b2-dev-vr1',
        'redis>=2.6.2',
        'isodate>=0.4.4',
    ],
    entry_points={
        'console_scripts': [
            'proc_publisher = raptor.publisher:main',
        ]
    },
    # Custom version of supervisor that supports proc add/delete events
    dependency_links = ['https://bitbucket.org/yougov/velociraptor/downloads/supervisor-3.0b2-dev-vr1.tar.gz#egg=supervisor-3.0b2-dev-vr1'],
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)
