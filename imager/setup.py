#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.imager',
    namespace_packages=['vr'],
    version='0.0.2',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'vr.runners>=2.4.2,<3',
        'PyYAML==3.10',
    ],
    entry_points={
        'console_scripts': [
            'vimage = vr.imager.main:main',
        ]
    },
    description=('Command line tool to create system image tarballs.'),
)
