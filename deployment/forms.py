from django import forms

from deployment.models import Deployment, Release, Host

class DeploymentModelForm(forms.ModelForm):
    class Meta:
        model = Deployment
        exclude = ('deployment_status',)

class DeploymentForm(forms.Form):

    _releases = [(r.id, r) for r in Release.objects.all()]
    release_id = forms.ChoiceField(choices=_releases)
    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    proc = forms.CharField(max_length=50)

    _hosts = [(h.name, h.name) for h in Host.objects.filter(active=True)]
    host = forms.ChoiceField(choices=_hosts)
    port = forms.IntegerField()

    user = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
