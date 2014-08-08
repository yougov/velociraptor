#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.agent',
    namespace_packages=['vr'],
    version='0.0.1',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyYAML==3.10',
        'redis>=2.6.2',
        'requests>=1.0.4',
        'supervisor',
        'vr.common>=2.15.2',
    ],
    entry_points={
        'console_scripts': [
            'proc_publisher = vr.agent.publisher:main',
        ]
    },
    description=('Velociraptor plugins to Supervisord.'),
)
