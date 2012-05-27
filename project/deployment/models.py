import xmlrpclib
import logging
import posixpath
import hashlib
import datetime
import collections

from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
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
    file = models.FileField(upload_to='builds', null=True, blank=True)

    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    build_status_choices = (
        ('pending', 'Pending'),
        ('started', 'Started'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    status = models.CharField(max_length=20, choices=build_status_choices,
                              default='pending')

    def __unicode__(self):
        # Return the app name and version
        return u'-'.join([self.app.name, self.tag])

    class Meta:
        ordering = ['-id']

from django.db import IntegrityError

class Release(models.Model):
    profile = models.ForeignKey(Profile)
    build = models.ForeignKey(Build)
    config = models.TextField(blank=True, null=True)

    # XXX Should we set a uniqueness constraint on the hash?  If we had that,
    # we could take any proc name from supervisord and look up the exact build
    # and config used for it.
    # Hash will be computed on saving the model.
    hash = models.CharField(max_length=32, blank=True, null=True)

    def __unicode__(self):
        return u'-'.join([self.build.app.name, self.build.tag,
                          self.profile.name, self.hash or 'PENDING'])

    def compute_hash(self):
        # Compute self.hash from the config contents and build file.
        buildcontents = default_storage.open(self.build.file.name, 'rb').read()

        md5chars = hashlib.md5(buildcontents + bytes(self.config)).hexdigest()
        return md5chars[:8]

    def save(self, *args, **kwargs):
        # If there's not a hash, and there *is* a build, then compute the hash
        if self.build.file.name:
            self.hash = self.compute_hash()
        super(Release, self).save(*args, **kwargs)

    def parsed_config(self):
        return yaml.safe_load(self.config or '')

    class Meta:
        ordering = ['-id']


class Host(models.Model):
    name = models.CharField(max_length=200, unique=True)

    # It might be hard to delete host records if there 
    active = models.BooleanField(default=True)
    squad = models.ForeignKey('Squad', null=True, blank=True, related_name='hosts')


    def __unicode__(self):
        squadname = self.squad.name if self.squad else '(no squad)'
        return '%s: %s' % (squadname, self.name)

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

    def get_next_port(self):
        # XXX There's a race condition here if one worker starts a deploy and
        # then another asks for a free port before the first is finished.
        # Solution: Add a lock to the ports returned here.  Either through a
        # field on this model (easy) or a file placed on the remote host
        # (perhaps better, but uglier to implement).

        all_ports = xrange(settings.PORT_RANGE_START, settings.PORT_RANGE_END)
        used_ports = self.get_used_ports()
        # Return the first port in our configured range that's not already in
        # use.
        return next(x for x in all_ports if x not in used_ports)


    def get_procs(self):
        server = xmlrpclib.Server('http://%s:%s' % (self.name, settings.SUPERVISOR_PORT))
        states = server.supervisor.getAllProcessInfo()
        # Query all hosts in the squad and get their list of procs.  Not quite
        # sure what should be returned though.  We need something that's easily
        # filterable.  So we'd really like to be able to say "how many of these
        # are running version A of app B with config from profile C?"  So I
        # think we want at least named tuples, with references to real objects.
        def make_proc(name, host):
            # Given the name of a proc like
            # 'khartoum-0.0.7-yfiles-1427a4e2-web-8060', parse out the bits and
            # return a named tuple.

            # XXX This function will throw DoesNotExist if either the app or
            # profile can't be looked up.  So careful with what you rename.
            parts = name.split('-')
            try:
                app = App.objects.get(name=parts[0])
                return Proc(
                    name=name,
                    app=app,
                    tag=parts[1],
                    profile=Profile.objects.get(app=app, name=parts[2]),
                    hash=parts[3],
                    proc=parts[4],
                    port=int(parts[5]),
                    host=host,
                )
            except ObjectDoesNotExist:
                return None

        # Filter out any procs for whom we couldn't look up an App or Profile
        procs = [make_proc(p['name'], self) for p in states]

        return [p for p in procs if p is not None]


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
        return self.name


class Proc(object):
    def __init__(self, name, app, tag, profile, hash, proc, host, port):
        self.name = name
        self.app = app
        self.tag = tag
        self.profile = profile
        self.hash = hash
        self.proc = proc
        self.host = host
        self.port = port

    def as_node(self):
        """
        Return host:port, as needed by the balancer interface.
        """
        return '%s:%s' % (self.host.name, self.port)


class Swarm(models.Model):
    """
    This is the payoff.  Save a swarm record and then you can tell Velociraptor
    to 'make it so'.
    """
    profile = models.ForeignKey(Profile)
    squad = models.ForeignKey(Squad)
    release = models.ForeignKey(Release)
    proc_name = models.CharField(max_length=50)
    size = models.IntegerField(help_text='The number of procs in the swarm',
                               default=1)

    pool_help = "The name of the pool in the load balancer (omit prefix)"
    pool = models.CharField(max_length=50, help_text=pool_help)

    # If set to true, then the workers will periodically check this swarm's
    # status and make sure it has enough workers, running the right version,
    # with the right config. 
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('profile', 'squad', 'proc_name')

    def __unicode__(self):
        rname = self.release.__unicode__()
        proc = self.proc_name
        size = self.size
        squad = self.squad.name
        return u'%(rname)s-%(proc)s X %(size)s on %(squad)s' % vars()

    def shortname(self):
        a = self.profile.app.name
        p = self.profile.name
        proc = self.proc_name
        return u'%(a)s-%(p)s-%(proc)s' % vars()


    def all_procs(self):
        """
        Return all running procs on the squad that share this swarm's profile.
        """
        if not self.release:
            return []

        procs = []
        for host in self.squad.hosts.all():
            procs += host.get_procs()

        return [p for p in procs if p.profile == self.profile]

    def current_procs(self):
        """
        Return all running procs on the squad that share this swarm's profile
        and release hash.
        """
        return [p for p in self.all_procs() if p.hash == self.release.hash]

    def stale_procs(self):
        """
        Return all running procs on the squad that share this swarm's profile
        but have a different release hash.
        """
        return [p for p in self.all_procs() if p.hash != self.release.hash]

    def get_next_host(self):
        """
        Sort hosts in the squad first by number of procs from this swarm, then
        by total number of procs.  Return the first host in that sorted list.
        """

        squad_hosts = list(self.squad.hosts.all())
        # cache the proc counts for each host
        for h in squad_hosts:
            all_procs = h.get_procs()
            swarm_procs = [p for p in all_procs if p.hash == self.release.hash]
            h.sortkey = (len(swarm_procs), len(all_procs))

        squad_hosts.sort(key=lambda h: h.sortkey)

        return squad_hosts[0]
