from django.db import models
from django.contrib.auth.models import User


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


class App(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class Build(models.Model):
    file = models.FileField(upload_to='builds/')
    app = models.ForeignKey(App)

    def __unicode__(self):
        return '%s:%s' % (self.app.name, self.file)

class Release(models.Model):
    build = models.ForeignKey(Build)

    # Store the config used for the release right here, in YAML form.  This
    # freezes it in time so we always know exactly what config went into a
    # release, without a lot of sleuthing.

    # To be determined: How we populate this field, whether through copy/paste,
    # or sucking values out of Puppet or something like Hiera, or storing
    # master config in this same DB. 

    # TODO: Create a YAMLField() field type that validates that the information
    # being saved is valid YAML.
    config = models.TextField()

    def __unicode__(self):
        return 'release %s of build %s' % (self.id, self.build)

(STATUS_DEPLOYING,
 STATUS_DEPLOYED,
 STATUS_DECOMMISSIONED) = xrange(3)

DEPLOYMENT_STATUS_CHOICES = (
    (STATUS_DEPLOYING, 'Deploying'),
    (STATUS_DEPLOYED, 'Deployed'),
    (STATUS_DECOMMISSIONED, 'Decommissioned'),
)

class Deployment(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    release = models.ForeignKey(Release)
    host = models.CharField(max_length=100)
    port = models.IntegerField()
    # 'proc' is the exact name used in the supervisord 'program' section.  So
    # you can use it in commands like 'supervisorctl stop <proc>'
    proc = models.CharField(max_length=100)

    # 'deployment_status' is where we record the current position of this
    # deployment in its lifecycle.  All deployments should start as
    # 'deploying'.  Then once they're running (as determined by supervisord and
    # smoke tests), they should be set to 'deployed'.  When they've been taken
    # down, they should be set to 'decommissioned'.  
    deployment_status = models.IntegerField(choices=DEPLOYMENT_STATUS_CHOICES)

    def __unicode__(self):
        # XXX This query for the app name will be expensive if you're in a loop
        # and do it a lot of times.  Perhaps we should just put app on
        # releases and deployments as well as builds?  Would be duplicative but
        # make for more efficient queries.  On the other hand, this method only
        # gets called when we're displaying deployments in the UI, so maybe
        # it's no big deal.
        app = self.release.build.app.name
        proc = self.proc
        host = self.host
        port = self.port
        return '%(app)s %(proc)s on %(host)s:%(port)s' % locals()
