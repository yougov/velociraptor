import xmlrpclib
import logging
import posixpath

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.serializers.pyyaml import DjangoSafeDumper
from django.core.exceptions import ValidationError

import yaml


LOG_ENTRY_TYPES = (
    ('build', 'Build'),
    ('release', 'Release'),
    ('deployment', 'Deployment'),
)

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


# XXX Once we require login everywhere, update this function to not be stupid.
def remember(msg_type, msg, username='brent'):
    logentry = DeploymentLogEntry(
        type=msg_type,
        user=User.objects.get(username=username),
        message=msg
    )
    logentry.save()
    # Also log it to actual python logging
    logging.info('%s %s: %s' % (msg_type, username, msg))

# TODO: revamp this to look like https://paste.yougov.net/LMMml

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

def rename_keys(d, translations):
    """
    Return a copy of dictionary 'd' where any keys also present in
    'translations' have been renamed according to that mapping.
    """
    print d
    if not translations:
        return d
    out = {}
    for k in d.keys():
        if k in translations:
            out[translations[k]] = d[k]
        else:
            out[k] = d[k]
    return out


class Profile(models.Model):
    name = models.CharField(max_length=50, unique=True)
    app = models.ForeignKey(App)
    configvalues = models.ManyToManyField(ConfigValue, through='ProfileConfig')

    def __unicode__(self):
        return self.name

    def assemble(self):
        out = {}
        for r in ProfileConfig.objects.filter(profile=self):
            out.update(rename_keys(r.configvalue.value, r.translations))
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

    ohelp = 'Order for merging when creating release.  Lowest to highest.'
    order = models.IntegerField(blank=True, null=True,  help_text=ohelp)

    thelp = 'Map for renaming configvalue keys to be more app-friendly'
    translations = YAMLDictField(blank=True, null=True, help_text=thelp)

    class Meta:
        unique_together = ('configvalue', 'profile')


class Build(models.Model):
    file = models.FileField(upload_to='builds')
    app = models.ForeignKey(App)

    def __unicode__(self):
        return str(self.file)


class Release(models.Model):
    build = models.ForeignKey(Build)
    config = YAMLDictField(blank=True, null=True)

    # TODO: Add a 'label' or 'profile_name' field to make for better release
    # naming.  It could also be used in the proc names to more easily
    # differentiate between android and chrome datamarts, for example, or
    # between panel sites based on the same build.

    def __unicode__(self):
        # XXX Not happy with this, but haven't been able to come up with a more
        # intuitive way to name a 'release'.  Maybe just an app name and a
        # counter?  Maybe include the name of the config profile once we have
        # those?
        return 'release %s of %s' % (self.id,
                                     posixpath.basename(self.build.file.name))


class Host(models.Model):
    name = models.CharField(max_length=200, unique=True)
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
