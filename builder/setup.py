#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.builder',
    namespace_packages=['vr'],
    version='0.0.1',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'vr.runners>=0.0.7',
        'PyYAML>=3.10',
    ],
    entry_points={
        'console_scripts': [
            'vbuild = vr.builder.main:main',
        ]
    },
    description=('Command line tools to launch procs.'),
)
