#!/usr/bin/python
from setuptools import setup

setup(
    name='vr',
    version='1.2',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=['vr',
              'vr.api',
              'vr.deployment',
              'vr.tests',
              'vr.deployment.balancer',
              'vr.deployment.migrations',
              'vr.deployment.templatetags'],
    include_package_data=True,
    install_requires=[
        'celery-schedulers==0.0.2',
        'Django==1.4',
        'django-celery==3.0.11',
        'django-extensions==0.7.1',
        'django-picklefield==0.2.0',
        'django-redis-cache==0.9.5',
        'django-reversion==1.6.1',
        'django-tastypie==0.9.12-alpha',
        'django-yamlfield==0.2',
        'gevent==1.0rc2',
        'gevent-psycopg2==0.0.3',
        'gunicorn==0.17.2',
        'psycopg2==2.4.4',
        'pymongo==2.1.1',
        'redis==2.6.2',
        'requests==1.0.4',
        'South==0.7.6',
        'sseclient==0.0.3',
    ],
    entry_points={
        'console_scripts': [
            'proc_publisher = raptor.publisher:main',
        ]
    },
    dependency_links = [
        'https://bitbucket.org/yougov/velociraptor/downloads/django-tastypie-0.9.12-alpha.tar.gz#egg=django-tastypie-0.9.12-alpha',
        'https://github.com/downloads/SiteSupport/gevent/gevent-1.0rc2.tar.gz#egg=gevent-1.0rc2'
    ],
    description=('Velociraptor Django project.'),
)
