import sys

if 'runserver' in sys.argv:
    from gevent import monkey
    monkey.patch_all()
    import gevent_psycopg2
    gevent_psycopg2.monkey_patch()

from socket import getfqdn

from datetime import timedelta
import os
import warnings

import djcelery
import pymongo


here = os.path.dirname(os.path.realpath(__file__))


# Add current folder to the sys path so that the 'deployment' app in the child
# folder ccan be imported.
if not here in sys.path:
    sys.path.insert(0, here)

parentpath = os.path.dirname(here)


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # Change this to the devops group email when we deploy this for real.
    ('Brent Tubbs', 'brent.tubbs@yougov.com'),
    ('Fernando Gutierrez', 'fernando.gutierrez@yougov.com'),
)

MANAGERS = ADMINS
SERVER_EMAIL = 'velociraptor@' + getfqdn()
CELERY_SEND_TASK_ERROR_EMAILS = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'velo',
        'USER': 'raptor',
        'PASSWORD': 'MZpuvFzZ',
        'HOST': 'localhost',
        'PORT': '',
    }
}

BALANCERS = {
    'default': {
        'BACKEND': 'deployment.balancer.dummy.DummyBalancer',
    }
}

# Without this, the build host will choke when trying to connect to a local
# redis that doesn't exist.
if 'collectstatic' not in sys.argv:
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': 'localhost:6379',
            'KEY_PREFIX': 'vrcache_',
            'OPTIONS': {
                'DB': 0,
            },
        },
    }

# UI Customization.  It's good to make your non-production instances look
# different from production.
SITE_TITLE = "Velociraptor"
# URL to a custom CSS file
CUSTOM_CSS = None

USE_TZ = True

# Username and password to be used when SSHing to hosts.  Set to
# 'vagrant/vagrant' by default for ease of development within a Vagrant VM.
DEPLOY_USER = 'vagrant'
DEPLOY_PASSWORD = 'vagrant'

# Suppress warnings when we pass a URI to MongoDB that includes the
#  database name.
warnings.filterwarnings('ignore', category=UserWarning,
    message="must provide a username",
    module='pymongo.connection')

MONGODB_URL = 'mongodb://localhost/velociraptor'

CELERY_ENABLE_UTC = True
CELERYBEAT_SCHEDULER = 'mongoscheduler.MongoScheduler'
CELERY_MONGO_SCHEDULER_URI = 'mongodb://localhost:27017/velociraptor.scheduler'

# Use Redis broker and results backend by default.  The RabbitMQ one isn't as
# nice for chords.
BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# A redis pubsub where worker procs can push events, and our fancy schmancy SSE
# streaming event views can push them out to browsers.
EVENTS_PUBSUB_URL = 'redis://localhost:6379/0'
EVENTS_PUBSUB_CHANNEL = 'vr_events'
EVENTS_BUFFER_KEY = 'vr_events_buffer'
EVENTS_BUFFER_LENGTH = 100

HOST_EVENTS_CHANNEL = 'vr_host_events'
HOST_EVENTS_BUFFER = 'vr_host_events_buffer'

CELERYBEAT_SCHEDULE = {
    'scooper': {
        'task': 'deployment.tasks.scooper',
        'schedule': timedelta(minutes=240),
        'options': {
            'expires': 120,
        },
    },
    'test_all_the_things': {
        'task': 'deployment.tasks.uptest_all_procs',
        'schedule': timedelta(minutes=30),
        'options': {
            'expires': 120,
        },
    },
}

SUPERVISOR_PORT = 9001
PORT_RANGE_START = 5000
PORT_RANGE_END = 6000

# Settings used when writing the proc.conf includes for supervisord
PROC_USER = 'nobody'
PROC_SYSLOG = False

# Local time zone for this installation.  On Unix systems, a value of None will
# cause Django to use the same timezone as the operating system.
TIME_ZONE = None

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = False
USE_L10N = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(here, 'uploads/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/uploads/'

# Store files using mongodb gridfs by default.
DEFAULT_FILE_STORAGE = 'deployment.storages.GridFSStorage'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CachedStaticFilesStorage'

STATIC_ROOT = os.path.join(here, 'static')

STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 't$fdltm55xt!a+chs_p-h9^7=-kh7@z$7salven903a%7v6c-i'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    os.path.join(here, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'deployment.context_processors.raptor',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
LOGIN_URL = '/login/'

ROOT_URLCONF = 'project.urls'

TEMPLATE_DIRS = (
    os.path.join(here, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'djcelery',
    'django_extensions',
    'deployment',   # Velociraptor UI
    'api',          # Velociraptor API
    'south',
    'reversion'
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

SUPERVISORD_WEB_PORT = 9001

# If BUILD_EXPIRATION_DAYS is set to an integer instead of None, then the
# celerybeat proc will run a task every day to clean up old builds.  Regardless
# of the date cutoff, builds that are currently in use will be kept around, as
# well as the N most recent builds up to BUILD_EXPIRATION_COUNT.
BUILD_EXPIRATION_DAYS = None
BUILD_EXPIRATION_COUNT = 10

# Allow production to override these settings.
if os.environ.get('APP_SETTINGS_YAML'):
    import yaml
    try:
        globals().update(yaml.safe_load(open(os.environ['APP_SETTINGS_YAML'])))
    except IOError:
        # Allow settings to be imported during build so we can compilestatic
        pass


# Unpack the MONGODB_URL env var to provide the settings that the GridFS
# storage wants.
mongoparts = pymongo.uri_parser.parse_uri(MONGODB_URL)
GRIDFS_HOST = mongoparts['nodelist'][0][0]
GRIDFS_PORT = mongoparts['nodelist'][0][1]
GRIDFS_DB = mongoparts['database'] or 'test'
GRIDFS_COLLECTION = mongoparts['collection'] or 'fs'

djcelery.setup_loader()

# Now that production settings have been patched in, schedule a task for build
# cleanup if necessary.
if BUILD_EXPIRATION_DAYS is not None:
    CELERYBEAT_SCHEDULE['build_cleanup'] = {
        'task': 'deployment.tasks.clean_old_builds',
        'schedule': timedelta(days=1),
        'options': {'expires': 120}
    }
