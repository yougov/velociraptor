import xmlrpclib
import logging
import posixpath
import hashlib
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.conf import settings
import yaml

from deployment.fields import YAMLDictField


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
    name = models.CharField(verbose_name="Profile Name", max_length=20, help_text=namehelp)
    configvalues = models.ManyToManyField(ConfigValue, through='ProfileConfig')

    def __unicode__(self):
        return '%s-%s' % (self.app.name, self.name)

    def assemble(self):
        out = {}
        for r in ProfileConfig.objects.filter(profile=self):
            translations = r.translations or {}
            out.update(rename_keys(r.configvalue.value, translations))
        return out

    def to_yaml(self):
        return yaml.safe_dump(self.assemble(), default_flow_style=False)

    class Meta:
        unique_together = ('app', 'name')


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
    file = models.FileField(upload_to='builds', null=True)

    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    build_status_choices = (
        ('started', 'Started'),
        ('success', 'Success'),
        ('failure', 'Failed'),
    )

    status = models.CharField(max_length=20, choices=build_status_choices)

    def __unicode__(self):
        return self.shortname()

    def shortname(self):
        # Return the app name and version
        return u'-'.join([self.app.name, self.tag])

    class Meta:
        ordering = ['-id']


class Release(models.Model):
    profile = models.ForeignKey(Profile, null=True)
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
                          self.rrofile_name, self.hash])

    def compute_hash(self):
        # Compute self.hash from the config contents and build file.
        buildcontents = default_storage.open(self.build.file.name).read()

        md5chars = hashlib.md5(buildcontents + self.config).hexdigest()
        return md5chars[:8]

    def save(self, *args, **kwargs):
        self.hash = self.compute_hash()
        super(Release, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-id']


class Host(models.Model):
    name = models.CharField(max_length=200, unique=True)

    # It might be hard to delete host records if there 
    active = models.BooleanField(default=True)
    squad = models.ForeignKey('Squad', null=True, related_name='hosts')


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


class Squad(models.Model):
    """
    A group of hosts.  They should be as identical as possible.
    """
    name = models.CharField(max_length=50)

    # Select which balancer should be used for this squad, from
    # settings.BALANCERS
    _balancer_choices = [(k, k) for k in settings.BALANCERS]
    balancer = models.CharField(max_length=50, choices=_balancer_choices)

    def __unicode__(self):
        return name


class Swarm(models.Model):
    """
    This is the payoff.  Save a swarm record and then you can tell Velociraptor
    to 'make it so'.
    """
    app = models.ForeignKey(App)
    tag = models.CharField(max_length=50)

    replaces = models.ForeignKey('Swarm')
    release = models.ForeignKey(Release)
    squad = models.ForeignKey(Squad)
    # TODO: ensure that the swarm we're replacing points to the same app and
    # squad as we do.  Possibly do this by only exposing the 'replaces' field
    # in the form, and filling the others from there.
    size = models.IntegerField(help_text='The number of procs in the swarm')

    # XXX Use profile name as the pool name?  That'd be neat. Would take manual
    # steps to ensure that match though, which could be a pain.  Suggest using
    # profile name as default in 'new swarm' form.
    pool_help = "The name of the pool in the load balancer (omit prefix)"
    pool = models.CharField(max_length=50, help_text=pool_help)

    # The time when you first tell Velociraptor to 'go'
    start_time = models.DateTimeField(null=True)

    # The time when all the procs have been deployed and are ready for
    # balancing
    ready_time = models.DateTimeField(null=True)

    # The time when this swarm is retired.  Typically after being replaced by a
    # new version.
    retire_time = models.DateTimeField(null=True)

    def __unicode__(self):
        release_name = self.release.__unicode__()
        size = self.size
        squad = self.squad.name
        return u'%(release_name)s X %(size)s on %(squad)s' % vars()

    def get_next_host(self):
        """
        Return the host that should be used for the next deployment.
        """
        # Query all hosts in the squad.  Sort first by number of procs from
        # this swarm, then by total number of procs.  Return the first host in
        # the sorted list.
        pass



