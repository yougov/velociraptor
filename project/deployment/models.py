import xmlrpclib
import logging
import posixpath

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

import yaml
from yamlfield.fields import YAMLField

LOG_ENTRY_TYPES = (
    ('build', 'Build'),
    ('release', 'Release'),
    ('deployment', 'Deployment'),
)

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
    value = YAMLField(help_text=("Must be valid YAML.  Simple strings and "
                                 "numbers are valid YAML."))

    def __unicode__(self):
        return u'%s (%s)' % (self.label, self.setting_name)


class App(models.Model):
    name = models.CharField(max_length=50)
    repo_url = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return self.name


class Profile(models.Model):
    name = models.CharField(max_length=50, unique=True)
    app = models.ForeignKey(App)
    configvalues = models.ManyToManyField(ConfigValue, through='ProfileConfig')

    def __unicode__(self):
        return self.name

    def assemble(self):
        out = {}
        for cv in self.configvalues.all():
            out[cv.setting_name] = cv.value
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
    translations = YAMLField(blank=True, null=True, help_text=thelp)

    class Meta:
        unique_together = ('configvalue', 'profile')



class Build(models.Model):
    file = models.FileField(upload_to='builds')
    app = models.ForeignKey(App)

    def __unicode__(self):
        return str(self.file)


class Release(models.Model):
    build = models.ForeignKey(Build)
    config = YAMLField()

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
