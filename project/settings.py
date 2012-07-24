from datetime import timedelta
import os
import sys
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'raptor_cache',
    }
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

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = "/"

CELERYBEAT_SCHEDULE = {
    'scooper': {
        'task': 'deployment.tasks.scooper',
        'schedule': timedelta(minutes=30),
    },
    'update_tags': {
        'task': 'deployment.tasks.update_tags',
        'schedule': timedelta(minutes=30),
    },
}

SUPERVISOR_PORT = 9001
PORT_RANGE_START = 5000
PORT_RANGE_END = 6000

# Settings used when writing the proc.conf includes for supervisord
PROC_USER = 'nobody'
PROC_SYSLOG = False

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False  # We all speak English.

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = False  # U.S.A.! U.S.A.!

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

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(here, 'static')


# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    #'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 't$fdltm55xt!a+chs_p-h9^7=-kh7@z$7salven903a%7v6c-i'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
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
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(here, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites', # Unneeded?
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'djcelery',
    'django_extensions',
    'deployment',  # Our main velociraptor app
    'south',
    'reversion'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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
