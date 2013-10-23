#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.runners',
    namespace_packages=['vr'],
    version='0.0.3',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'vr.common>=3.5',
        'requests>=1.2.0',
        'PyYAML>=3.10',
    ],
    entry_points={
        'console_scripts': [
            'vrun_precise = vr.runners.precise:main',
        ]
    },
    description=('Command line tools to launch procs.'),
)
