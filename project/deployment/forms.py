from django import forms
from django.contrib.auth import authenticate

from deployment import models


class BuildForm(forms.Form):

    app_id = forms.ChoiceField(choices=[], label='App')
    tag = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(BuildForm, self).__init__(*args, **kwargs)
        self.fields['app_id'].choices = [(a.id, a) for a in models.App.objects.all()]


class BuildUploadForm(forms.ModelForm):
    class Meta:
        model = models.Build

class ReleaseForm(forms.Form):
    build_id = forms.ChoiceField(choices=[], label='Build')
    profile_id = forms.ChoiceField(choices=[], label='Profile')

    def __init__(self, *args, **kwargs):
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields['build_id'].choices = [(b.id, b) for b in
                                           models.Build.objects.all()]
        self.fields['profile_id'].choices = [(p.id, p) for p in
                                             models.Profile.objects.all()]

    def clean(self):
        # Look up the build's app, and the profile's app, and make sure they
        # match.
        build = models.Build.objects.get(id=self.cleaned_data['build_id'])
        profile = models.Profile.objects.get(id=self.cleaned_data['profile_id'])
        if not build.app.id == profile.app.id:
            raise forms.ValidationError("Build app doesn't match Profile app")
        return self.cleaned_data


class DeploymentForm(forms.Form):

    release_id = forms.ChoiceField(choices=[], label='Release')
    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    proc = forms.CharField(max_length=50)

    host = forms.ChoiceField(choices=[])
    port = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(DeploymentForm, self).__init__(*args, **kwargs)
        self.fields['release_id'].choices = [(r.id, r) for r in models.Release.objects.all()]
        self.fields['host'].choices = [(h.name, h.name) for h in
                                       models.Host.objects.filter(active=True)]


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        self.user = authenticate(**self.cleaned_data)
        if not self.user:
            raise forms.ValidationError('Bad username or password')
        return self.cleaned_data


class SwarmForm(forms.Form):
    """
    Form for creating a new swarm.
    """
    release_id = forms.ChoiceField(choices=[], label='Release')
    squad_id = forms.ChoiceField(choices=[], label='Squad')
    size = forms.IntegerField()
    pool = forms.CharField(max_length=50)

    def __init__(self, data, *args, **kwargs):
        super(SwarmForm, self).__init__(data, *args, **kwargs)



class ReswarmForm(forms.Form):
    """
    Form for replacing an existing swarm with a new one; changing the size,
    version, or config.
    """
    tag = forms.CharField(max_length=50)
    profile_id = forms.ChoiceField(choices=[], label='Profile')
    size = forms.IntegerField()

    def __init__(self, data, swarm, *args, **kwargs):
        initial = {}
        if swarm is not None:
            initial.update(
                tag=swarm.tag,
                size=swarm.size,
            )
            if swarm.release is not None:
                initial['profile_id'] = swarm.release.profile.id
        super(ReswarmForm, self).__init__(data, *args, initial=initial, **kwargs)

        self.fields['profile_id'].choices = [(p.id, p) for p in
                                             models.Profile.objects.all()]
