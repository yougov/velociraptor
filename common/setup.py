#!/usr/bin/python

import setuptools

params = dict(
    name='vr.common',
    version='4.0',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    url='https://bitbucket.org/yougov/velociraptor',
    description='Libraries and for deploying with Velociraptor',

    packages=setuptools.find_packages(),
    namespace_packages=['vr'],
    include_package_data=True,

    install_requires=[
        'isodate>=0.4.4',
        'six>=1.4.1',
        'utc',
        'requests',
        'PyYAML>=3.10',
        'sseclient==0.0.8',
    ],

    extras_require={
        ':python_version=="2.7"': [
            'suds==0.4',
        ],
    },
)

if __name__ == '__main__':
    setuptools.setup(**params)
