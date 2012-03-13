from django import forms

from deployment.models import Deployment, Release

class DeploymentModelForm(forms.ModelForm):
    class Meta:
        model = Deployment
        exclude = ('deployment_status',)

HOSTS = (
    'devbrent.paloalto.yougov.net',
    'xstageulus.paix.yougov.net',
    'datamart-dev.paix.yougov.net',
)

class DeploymentForm(forms.Form):

    _choices = [(x.id, x) for x in Release.objects.all()]
    release = forms.ChoiceField(choices=_choices)
    host = forms.ChoiceField(choices=[(x, x) for x in HOSTS])
    port = forms.IntegerField()

    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    #proc

    user = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
