#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='raptor',
    version='2.3.1',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'paramiko>=1.8.0,<2.0',
        'envoy==0.0.2',
        'suds==0.4',
        'supervisor>=3.0b1',
        'redis>=2.6.2',
    ],
    entry_points={
        'console_scripts': [
            'proc_publisher = raptor.publisher:main',
        ]
    },
    description=('Libraries and command line tools for deploying with '
                 'Velociraptor'),
)
