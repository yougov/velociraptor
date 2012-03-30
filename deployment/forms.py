from django import forms

from deployment.models import Release, Host, App, Build


class BuildForm(forms.Form):

    app_id = forms.ChoiceField(choices=[], label='App')
    tag = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(BuildForm, self).__init__(*args, **kwargs)
        self.fields['app_id'].choices = [(a.id, a) for a in App.objects.all()]


class BuildUploadForm(forms.ModelForm):
    class Meta:
        model = Build

class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release


class DeploymentForm(forms.Form):

    release_id = forms.ChoiceField(choices=[])
    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    proc = forms.CharField(max_length=50)

    host = forms.ChoiceField(choices=[])
    port = forms.IntegerField()

    user = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(DeploymentForm, self).__init__(*args, **kwargs)
        self.fields['release_id'].choices = [(r.id, r) for r in
                                             Release.objects.all()]
        self.fields['host'].choices = [(h.name, h.name) for h in
                                       Host.objects.filter(active=True)]
