from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.admin.widgets import FilteredSelectMultiple

import yaml

from vr.deployment import models


class ConfigIngredientForm(forms.ModelForm):
    class Meta:
        model = models.ConfigIngredient

    class Media:
        js = (
            'js/jquery.textarea.min.js',
        )


    def clean_config_yaml(self):
        config_yaml = self.cleaned_data.get('config_yaml', None)
        if config_yaml:
            try:
                yaml.safe_load(config_yaml)
            except:
                raise forms.ValidationError("Invalid YAML")
        return config_yaml

    def clean_env_yaml(self):
        env_yaml = self.cleaned_data.get('env_yaml', None)
        if env_yaml:
            try:
                yaml.safe_load(env_yaml)
            except:
                raise forms.ValidationError("Invalid YAML")
        return env_yaml


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

    config_name = forms.CharField(help_text=models.config_name_help)

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
    config_name = forms.CharField(max_length=50,
                                  help_text=models.config_name_help)
    config_yaml = forms.CharField(required=False,
                                  widget=forms.widgets.Textarea(attrs={'class':
                                                                       'codearea'}))
    env_yaml = forms.CharField(required=False,
                               widget=forms.widgets.Textarea(attrs={'class':
                                                                    'codearea'}))
    proc_name = forms.CharField(max_length=50)
    squad_id = forms.ChoiceField(choices=[], label='Squad')
    size = forms.IntegerField()
    pool = forms.CharField(max_length=50, required=False)

    balancer_help = "Required if a pool is specified."
    balancer = forms.ChoiceField(choices=[], label='Balancer', required=False,
                                 help_text=balancer_help)

    config_ingredients = forms.ModelMultipleChoiceField(
        queryset=models.ConfigIngredient.objects.all(), required=False)

    def __init__(self, data, *args, **kwargs):
        if 'instance' in kwargs:
            # We get the 'initial' keyword argument or initialize it
            # as a dict if it didn't exist.
            initial = kwargs.setdefault('initial', {})
            # The widget for a ModelMultipleChoiceField expects
            # a list of primary key for the selected data.
            initial['config_ingredients'] = [
                c.pk for c in kwargs['instance'].configingredient_set.all()]

        super(SwarmForm, self).__init__(data, *args, **kwargs)
        self.fields['squad_id'].choices = [(s.id, s) for s in
                                            models.Squad.objects.all()]
        self.fields['app_id'].choices = [(a.id, a) for a in
                                            models.App.objects.all()]
        self.fields['balancer'].choices = [('', '-------')] + [
            (b, b) for b in settings.BALANCERS]

    def clean(self):
        data = super(SwarmForm, self).clean()
        if data['pool'] and not data['balancer']:
            raise forms.ValidationError('Swarms that specify a pool must '
                                        'specify a balancer')
        return data

    def save(self):
        instance = super(SwarmForm, self).save()
        instance.configingredient_set.clear()
        for ing in self.cleaned_data['config_ingredients']:
            instance.configingredient_set.add(ing)
        return instance

    class Media:
        js = (
            'js/jquery.textarea.min.js',
            'js/multiselect.js',
        )

        css = {
            'all': ('css/multiselect.css',),
        }
