import xmlrpclib
import logging
import posixpath
import hashlib
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.serializers.pyyaml import DjangoSafeDumper
from django.core.exceptions import ValidationError
from south.modelsinspector import add_introspection_rules
import yaml


LOG_ENTRY_TYPES = (
    ('build', 'Build'),
    ('release', 'Release'),
    ('deployment', 'Deployment'),
)

# Let South know how to handle our custom field type
add_introspection_rules([], ["^deployment\.models\.YAMLDictField"])

def validate_yaml_dict(value):
    if (value is not None and
        value != '' and
        not isinstance(value, dict)):
        raise ValidationError

class YAMLDictField(models.TextField):
    """
    YAMLDictField is a TextField that serializes and deserializes YAML dicts
    from the database.

    Based on https://github.com/datadesk/django-yamlfield, but goes one step
    further by ensuring that the data is a dict (or null), not just any valid
    yaml.
    """
    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(YAMLDictField, self).__init__(*args, **kwargs)
        self.validators.append(validate_yaml_dict)

    def to_python(self, value):
        """
        Convert our YAML string to a Python dict after we load it from the DB.
        Complain if it's not a dict.
        """
        if not value:
            return None

        # Seems like sometimes Django will pass a string into this function,
        # and other times a dict.  Pass out a dict either way.
        if isinstance(value, basestring):
            value = yaml.safe_load(value)

        return value

    def get_db_prep_save(self, value, connection, prepared=False):
        """
        Convert our Python object to a string of YAML before we save.
        """
        if not value:
            return ""

        value = yaml.dump(value, Dumper=DjangoSafeDumper,
                          default_flow_style=False)
        return super(YAMLDictField, self).get_db_prep_save(value, connection)

    def value_from_object(self, obj):
        """
        Returns the value of this field in the given model instance.

        We need to override this so that the YAML comes out properly formatted
        in the admin widget.
        """
        value = getattr(obj, self.attname)
        if not value or value == "":
            return value
        return yaml.dump(value, Dumper=DjangoSafeDumper,
            default_flow_style=False)


class DeploymentLogEntry(models.Model):
    type = models.CharField(max_length=50, choices=LOG_ENTRY_TYPES)
    time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    message = models.TextField()

    def __unicode__(self):
        return self.message

    class Meta:
        ordering = ['-time']


def remember(msg_type, msg, username):
    # Log to DB
    logentry = DeploymentLogEntry(
        type=msg_type,
        user=User.objects.get(username=username),
        message=msg
    )
    logentry.save()
    # Also log it to actual python logging
    logging.info('%s %s: %s' % (msg_type, username, msg))


class ConfigValue(models.Model):
    label = models.CharField(max_length=50, unique=True)
    value = YAMLDictField(help_text=("Must be valid YAML dict."))

    def __unicode__(self):
        return self.label


class App(models.Model):
    name = models.CharField(max_length=50)
    repo_url = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return self.name


def rename_keys(source, translations):
    """
    Return a copy of dictionary 'source' where any keys also present in
    'translations' have been renamed according to that mapping.

    >>> rename_keys(dict(a=1,b=2), dict(a='c')) == dict(c=1, b=2)
    True
    """
    return {
        translations.get(key, key): source[key]
        for key in source
    }


class Profile(models.Model):
    app = models.ForeignKey(App)
    namehelp = ("Used in release name.  Good profile names are short and use "
                "no spaces or dashes (underscores are OK)")
    name = models.CharField(verbose_name="Profile Name", max_length=20, unique=True, help_text=namehelp)
    configvalues = models.ManyToManyField(ConfigValue, through='ProfileConfig')

    def __unicode__(self):
        return '%s: %s' % (self.app.name, self.name)

    def assemble(self):
        out = {}
        for r in ProfileConfig.objects.filter(profile=self):
            translations = r.translations or {}
            out.update(rename_keys(r.configvalue.value, translations))
        return out

    def to_yaml(self):
        return yaml.safe_dump(self.assemble(), default_flow_style=False)


class ProfileConfig(models.Model):
    """
    Through-table for the many:many relationship between configvalues and
    profiles.  Managed manually so we can have some extra fields.
    """
    configvalue = models.ForeignKey(ConfigValue)
    profile = models.ForeignKey(Profile)

    ohelp = 'Order for merging when creating release. Higher number takes precedence.'
    order = models.IntegerField(blank=True, null=True,  help_text=ohelp)

    thelp = 'Map for renaming configvalue keys to be more app-friendly'
    translations = YAMLDictField(blank=True, null=True, help_text=thelp)

    class Meta:
        unique_together = ('configvalue', 'profile')


class Build(models.Model):
    app = models.ForeignKey(App)
    tag = models.CharField(max_length=50)
    file = models.FileField(upload_to='builds')

    # Don't use auto_now_add, because we want to be able to override this.
    time = models.DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return self.shortname()

    def shortname(self):
        # Return the app name and version
        return u'-'.join([self.app.name, self.tag])

    class Meta:
        ordering = ['-id']


class Release(models.Model):
    profile_name = models.CharField(max_length=20)
    build = models.ForeignKey(Build)

    # We used to use a YAMLDictField for release.config, but that has
    # possibility for the config saved at release time to not have the same key
    # ordering as the config written at deploy time, since Python dict key
    # ordering is not reliable.  Our apps wouldn't care, but it would mean we'd
    # get inconsistent release hashes at those two times.
    config = models.TextField(blank=True, null=True)

    # No need to set this in the admin.  We'll compute it on save.
    hash = models.CharField(max_length=32)

    def __unicode__(self):
        return u'-'.join([self.build.app.name, self.build.tag,
                          self.profile_name, self.hash])

    def compute_hash(self):
        # Compute self.hash from the config contents and build file.
        buildcontents = default_storage.open(self.build.file.name).read()

        md5chars = hashlib.md5(buildcontents + self.config).hexdigest()
        return md5chars[:8]

    def save(self, *args, **kwargs):
        self.hash = self.compute_hash()
        super(Release, self).save(*args, **kwargs)


class Host(models.Model):
    name = models.CharField(max_length=200, unique=True)

    # It might be hard to delete host records if there 
    active = models.BooleanField(default=True)


    def __unicode__(self):
        return self.name

    def get_used_ports(self):
        server = xmlrpclib.Server('http://%s:%s' % (self.name, settings.SUPERVISOR_PORT))
        states = server.supervisor.getAllProcessInfo()
        # names will look like 'thumpy-0.0.1-9585c1f8-web-8001'
        # split off the port at the end.
        ports = set()
        for proc in states:
            parts = proc['name'].split('-')
            if parts[-1].isdigit():
                ports.add(int(parts[-1]))
        return ports

    def get_unused_port(self):
        all_ports = xrange(settings.PORT_RANGE_START, settings.PORT_RANGE_END)
        used_ports = self.get_used_ports()
        # Return the first port in our configured range that's not already in
        # use.
        return next(x for x in all_ports if x not in used_ports)


