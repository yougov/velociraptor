import xmlrpclib
import logging
import posixpath

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

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


# XXX Right now settings are uploaded as a file each time you want to do a
# release.  Soon we want to switch that so that config is stored in the DB, and
# apps have 'profiles' of the config values they care about, which will be
# written into a settings.yaml at release time, and placed on the host at
# deploy time.
class ConfigValue(models.Model):
    name = models.CharField(max_length=50, unique=True)
    # Config values must be valid yaml.  This is validated on the way in, and
    # parsed automatically on the way out.
    value = YAMLField()

    def __unicode__(self):
        return self.name


class App(models.Model):
    name = models.CharField(max_length=50)
    repo_url = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return self.name


class Build(models.Model):
    file = models.FileField(upload_to='builds')
    app = models.ForeignKey(App)

    def __unicode__(self):
        return str(self.file)


class Release(models.Model):
    build = models.ForeignKey(Build)
    config = models.FileField(upload_to='configs')

    def __unicode__(self):
        # XXX Not happy with this, but haven't been able to come up with a more
        # intuitive way to name a 'release'.  Maybe just an app name and a
        # counter?  Maybe include the name of the config profile once we have
        # those?
        return 'release %s of %s' % (self.id,
                                     posixpath.basename(self.build.file.path))


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
