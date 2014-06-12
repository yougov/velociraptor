#!/usr/bin/env python
import setuptools

with open('README.txt') as readme:
    long_description = readme.read()
with open('CHANGES.txt') as changes:
    long_description += '\n\n' + changes.read()

setup_params = dict(
    name='vr.events',
    namespace_packages=['vr'],
    version="1.1.1",
    author="Jason R. Coombs",
    author_email="jaraco@jaraco.com",
    description="vr.events",
    long_description=long_description,
    url="https://bitbucket.org/yougov/vr.events",
    packages=setuptools.find_packages(),
    install_requires=[
        'vr.common',
        'six',
        'redis',
    ],
)
if __name__ == '__main__':
    setuptools.setup(**setup_params)
