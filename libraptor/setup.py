#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='raptor',
    version='2.1',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'paramiko>=1.8.0,<2.0',
        'vcstools==0.1.20',
        'envoy==0.0.2',
    ],
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)
