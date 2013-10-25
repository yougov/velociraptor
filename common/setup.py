#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.common',
    namespace_packages=['vr'],
    version='3.5.1',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'isodate>=0.4.4',
        'six',
        'suds==0.4',
        'utc',
    ],
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)
