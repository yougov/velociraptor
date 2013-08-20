#!/usr/bin/python
from setuptools import setup, find_packages

setup(
    name='vr.server',
    namespace_packages=['vr'],
    version='3.1.2',
    author='Brent Tubbs',
    author_email='brent.tubbs@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'celery-schedulers==0.0.2',
        'Django>=1.4,<1.5',
        'django-celery>=3.0.11,<3.1',
        'django-extensions==0.7.1',
        'django-picklefield==0.2.0',
        'django-redis-cache==0.9.5',
        'django-reversion==1.6.1',
        'django-tastypie==0.9.12-alpha',
        'django-yamlfield==0.2',
        'gevent>=1.0rc2,<2',
        'gevent-psycopg2==0.0.3',
        'gunicorn==0.17.2',
        'psycopg2>=2.4.4,<2.5',
        'pymongo>=2.5.2,<3',
        'redis>=2.6.2,<3',
        'requests==1.0.4',
        'South==0.7.6',
        'sseclient==0.0.4',
    ],
    dependency_links = [
        'https://bitbucket.org/yougov/velociraptor/downloads/django-tastypie-0.9.12-alpha.tar.gz#egg=django-tastypie-0.9.12-alpha',
        'https://github.com/downloads/surfly/gevent/gevent-1.0rc2.tar.gz#egg=gevent-1.0rc2'
    ],
    entry_points = {
        'console_scripts': [
            'vr_worker = vr.server.commands:start_celery',
            'vr_beat = vr.server.commands:start_celerybeat',
        ],
    },
    description=("Velociraptor's Django and Celery components."),
)
