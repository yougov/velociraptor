import xmlrpclib
import logging
import hashlib

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.storage import default_storage

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

class ConfigIngredient(models.Model):
    label = models.CharField(max_length=50, unique=True)
    value = YAMLDictField(help_text=("Must be valid YAML dict."))

    def __unicode__(self):
        return self.label

    class Meta:
        ordering = ['label', ]

class App(models.Model):
    namehelp = ("Used in release name.  Good app names are short and use "
                "no spaces or dashes (underscores are OK).")
    name = models.CharField(max_length=50, help_text=namehelp)
    repo_url = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ConfigRecipe(models.Model):
    app = models.ForeignKey(App)
    namehelp = ("Used in release name.  Good recipe names are short and use "
                "no spaces or dashes (underscores are OK)")
    name = models.CharField(verbose_name="ConfigRecipe Name", max_length=20,
                            help_text=namehelp)
    ingredients = models.ManyToManyField(ConfigIngredient,
                                         through='RecipeIngredient')

    def __unicode__(self):
        return '%s-%s' % (self.app.name, self.name)

    def assemble(self, custom_ingredients=None):
        """ Use current RecipeIngredients objects to assemble a dict of
        options, or use a custom list of ConfigIngredient ids that might
        be generated from a preview view. """
        out = {}
        if custom_ingredients is None:
            ingredients = [i.ingredient for i in
                           RecipeIngredient.objects.filter(recipe=self)]
        else:
            ingredients = ConfigIngredient.objects.filter(
                id__in=custom_ingredients)

        for i in ingredients:
            out.update(i.value)

        return out

    def to_yaml(self, custom_dict=None):
        """ Use assemble method to build a yaml file, or use a custom_dict
        that might be constructed from a preview view """
        if custom_dict is None:
            return yaml.safe_dump(self.assemble(), default_flow_style=False)
        else:
            return yaml.safe_dump(custom_dict, default_flow_style=False)

    class Meta:
        unique_together = ('app', 'name')


class RecipeIngredient(models.Model):
    """
    Through-table for the many:many relationship between configingredients and
    configrecipes.  Managed manually so we can have some extra fields.
    """
    ingredient = models.ForeignKey(ConfigIngredient)
    recipe = models.ForeignKey(ConfigRecipe)

    ohelp = "Order for merging when creating release. Higher number takes "\
            "precedence."
    order = models.IntegerField(blank=True, null=True,  help_text=ohelp)

    class Meta:
        unique_together = ('ingredient', 'recipe')


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


class Release(models.Model):
    recipe = models.ForeignKey(ConfigRecipe)
    build = models.ForeignKey(Build)
    config = models.TextField(blank=True, null=True)

    # Hash will be computed on saving the model.
    hash = models.CharField(max_length=32, blank=True, null=True)

    def __unicode__(self):
        return u'-'.join([self.build.app.name, self.build.tag,
                          self.recipe.name, self.hash or 'PENDING'])

    def compute_hash(self):
        # Compute self.hash from the config contents and build file.
        buildcontents = default_storage.open(self.build.file.name, 'rb').read()

        md5chars = hashlib.md5(buildcontents + bytes(self.config)).hexdigest()
        return md5chars[:8]

    def save(self, *args, **kwargs):
        # If there's a build, then compute the hash
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
    squad = models.ForeignKey('Squad', null=True, blank=True,
                              related_name='hosts')

    def __unicode__(self):
        return self.name

    def get_used_ports(self):
        server = xmlrpclib.Server('http://%s:%s' % (self.name,
                                                    settings.SUPERVISOR_PORT))
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

        all_ports = xrange(settings.PORT_RANGE_START, settings.PORT_RANGE_END)
        used_ports = self.get_used_ports()

        # Return the first port in our configured range that's not already in
        # use.
        def free(port):
            if PortLock.objects.filter(host=self, port=port):
                return False

            return port not in used_ports

        return next(x for x in all_ports if free(x))

    def get_procs(self):
        """
        Return a list of Proc objects, one for each supervisord process that
        has a parseable name and whose app and recipe can be found in the DB.
        """
        server = xmlrpclib.Server('http://%s:%s' % (self.name,
                                                    settings.SUPERVISOR_PORT))
        states = server.supervisor.getAllProcessInfo()

        def make_proc(name, host):
            # Given the name of a proc like
            # 'khartoum-0.0.7-yfiles-1427a4e2-web-8060', parse out the bits and
            # return a Proc object.

            # XXX This function will throw DoesNotExist if either the app or
            # recipe can't be looked up.  So careful with what you rename.
            parts = name.split('-')
            try:
                app = App.objects.get(name=parts[0])
                return Proc(
                    name=name,
                    app=app,
                    tag=parts[1],
                    recipe=ConfigRecipe.objects.get(app=app, name=parts[2]),
                    hash=parts[3],
                    proc=parts[4],
                    port=int(parts[5]),
                    host=host,
                )
            except ObjectDoesNotExist:
                return None

        procs = [make_proc(p['name'], self) for p in states]

        # Filter out any procs for whom we couldn't look up an App or
        # ConfigRecipe
        return [p for p in procs if p is not None]

    class Meta:
        ordering = ['name', ]


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
    def __init__(self, name, app, tag, recipe, hash, proc, host, port):
        self.name = name
        self.app = app
        self.tag = tag
        self.recipe = recipe
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
    recipe = models.ForeignKey(ConfigRecipe)
    squad = models.ForeignKey(Squad)
    release = models.ForeignKey(Release)
    proc_name = models.CharField(max_length=50)
    size = models.IntegerField(help_text='The number of procs in the swarm',
                               default=1)

    pool_help = "The name of the pool in the load balancer (omit prefix)"
    pool = models.CharField(max_length=50, help_text=pool_help, blank=True,
                            null=True)

    # If set to true, then the workers will periodically check this swarm's
    # status and make sure it has enough workers, running the right version,
    # with the right config.
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('recipe', 'squad', 'proc_name')
        ordering = ['recipe__app__name']

    def __unicode__(self):
        rname = self.release.__unicode__()
        proc = self.proc_name
        size = self.size
        squad = self.squad.name
        return u'%(rname)s-%(proc)s X %(size)s on %(squad)s' % vars()

    def shortname(self):
        a = self.recipe.app.name
        p = self.recipe.name
        proc = self.proc_name
        return u'%(a)s-%(p)s-%(proc)s' % vars()

    def all_procs(self):
        """
        Return all running procs on the squad that share this swarm's recipe.
        """
        if not self.release:
            return []

        procs = []
        for host in self.squad.hosts.all():
            procs += host.get_procs()

        return [p for p in procs if p.recipe == self.recipe and p.proc ==
                self.proc_name]

    def get_prioritized_hosts(self):
        """
        Return list of hosts in the squad sorted first by number of procs from
        this swarm, then by total number of procs.
        """
        squad_hosts = list(self.squad.hosts.all())
        # cache the proc counts for each host
        for h in squad_hosts:
            h.all_procs = h.get_procs()
            h.swarm_procs = [p for p in h.all_procs if p.hash ==
                             self.release.hash]
            h.sortkey = (len(h.swarm_procs), len(h.all_procs))

        squad_hosts.sort(key=lambda h: h.sortkey)
        return squad_hosts

    def get_next_host(self):
        return self.get_prioritized_hosts()[0]


class PortLock(models.Model):
    """
    The presence of one of these records indicates that a port is reserved for
    a particular proc that's probably still in the process of being deployed.
    Port locks should be deleted when their deploys are finished.
    """
    host = models.ForeignKey(Host)
    port = models.IntegerField()
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('host', 'port')

    def __unicode__(self):
        return '%s:%s' % (self.host, self.port)
