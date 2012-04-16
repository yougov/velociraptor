from django import forms

from deployment.models import Release, Host, App, Build, Profile


class BuildForm(forms.Form):

    app_id = forms.ChoiceField(choices=[], label='App')
    tag = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(BuildForm, self).__init__(*args, **kwargs)
        self.fields['app_id'].choices = [(a.id, a) for a in App.objects.all()]


class BuildUploadForm(forms.ModelForm):
    class Meta:
        model = Build

class ReleaseForm(forms.Form):
    build_id = forms.ChoiceField(choices=[], label='Build')
    profile_id = forms.ChoiceField(choices=[], label='Profile')

    def __init__(self, *args, **kwargs):
        super(ReleaseForm, self).__init__(*args, **kwargs)
        # TODO: somehow ensure that profile.app == build.app.  Maybe by only
        # listing a specific app's builds/profiles here?
        self.fields['build_id'].choices = [(b.id, b) for b in Build.objects.all()]
        self.fields['profile_id'].choices = [(p.id, p) for p in
                                             Profile.objects.all()]


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
            sorted(Release.objects.all(), key=lambda r: r.id, reverse=True)]
        self.fields['host'].choices = [(h.name, h.name) for h in
                                       Host.objects.filter(active=True)]


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        raise forms.ValidationError('you are invalid!')
        return self.cleaned_data
