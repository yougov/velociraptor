from django import forms
from django.conf import settings
from django.contrib.auth import authenticate

import yaml

from vr.deployment import models


class ConfigIngredientForm(forms.ModelForm):
    class Meta:
        model = models.ConfigIngredient

    def clean_value(self):
        value = self.cleaned_data.get('value', None)
        if value:
            try:
                yaml.safe_load(value)
            except:
                raise forms.ValidationError("Invalid YAML")
        return value


class BuildForm(forms.Form):

    app_id = forms.ChoiceField(choices=[], label='App')
    tag = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(BuildForm, self).__init__(*args, **kwargs)
        self.fields['app_id'].choices = [(a.id, a) for a in
                                         models.App.objects.all()]


class BuildUploadForm(forms.ModelForm):
    class Meta:
        model = models.Build


class SquadForm(forms.ModelForm):
    class Meta:
        model = models.Squad


class HostForm(forms.ModelForm):
    class Meta:
        model = models.Host


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = models.Release


class DeploymentForm(forms.Form):

    release_id = forms.ChoiceField(choices=[], label='Release')
    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    proc = forms.CharField(max_length=50)

    name_help = ("Distinguish between app instances with different config. "
                 "Must be filesystem safe and have no dashes or spaces.  App "
                 "name and version will be prepended automatically.")
    swarm_name = forms.CharField(help_text=name_help)

    hostname = forms.ChoiceField(choices=[])
    port = forms.IntegerField()
    contain = forms.BooleanField(help_text="Run inside LXC container?")

    def __init__(self, *args, **kwargs):
        super(DeploymentForm, self).__init__(*args, **kwargs)
        self.fields['release_id'].choices = [(r.id, r) for r in
            models.Release.objects.all()]
        self.fields['hostname'].choices = [(h.name, h.name) for h in
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
    Form for creating or updating a swarm.
    """
    app_id = forms.ChoiceField(choices=[], label='App')
    tag = forms.CharField(max_length=50)
    swarm_name = forms.CharField(max_length=50)
    proc_name = forms.CharField(max_length=50)
    squad_id = forms.ChoiceField(choices=[], label='Squad')
    size = forms.IntegerField()
    pool = forms.CharField(max_length=50, required=False)

    balancer_help = "Required if a pool is specified."
    balancer = forms.ChoiceField(choices=[], label='Balancer', required=False,
                                 help_text=balancer_help)

    def __init__(self, data, *args, **kwargs):
        super(SwarmForm, self).__init__(data, *args, **kwargs)
        self.fields['squad_id'].choices = [(s.id, s) for s in
                                            models.Squad.objects.all()]
        self.fields['app_id'].choices = [(a.id, a) for a in
                                            models.App.objects.all()]
        self.fields['balancer'].choices = [('', '-------')] + [(b, b) for b in
                                                               settings.BALANCERS]

    def clean(self):
        data = super(SwarmForm, self).clean()
        if data['pool'] and not data['balancer']:
            raise forms.ValidationError('Swarms that specify a pool must '
                                        'specify a balancer')
        return data

    class Media:
        js = (
            'js/dash_preview_recipe.js',
        )

