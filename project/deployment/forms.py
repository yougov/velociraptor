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
    recipe_id = forms.ChoiceField(choices=[], label='Recipe')

    def __init__(self, *args, **kwargs):
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields['build_id'].choices = [(b.id, b) for b in
                                           models.Build.objects.all()]
        self.fields['recipe_id'].choices = [(p.id, p) for p in
                                             models.ConfigRecipe.objects.all()]

    def clean(self):
        # Look up the build's app, and the recipe's app, and make sure they
        # match.
        build = models.Build.objects.get(id=self.cleaned_data['build_id'])
        recipe = models.ConfigRecipe.objects.get(id=self.cleaned_data['recipe_id'])
        if not build.app.id == recipe.app.id:
            raise forms.ValidationError("Build app doesn't match Recipe app")
        return self.cleaned_data


class DeploymentForm(forms.Form):

    release_id = forms.ChoiceField(choices=[], label='Release')
    # TODO: proc should be a drop down of the procs available for a given
    # release.  But I guess we can't narrow that down until a release is
    # picked.
    proc = forms.CharField(max_length=50)

    hostname = forms.ChoiceField(choices=[])
    port = forms.IntegerField()

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
    recipe_id = forms.ChoiceField(choices=[], label='Recipe')
    squad_id = forms.ChoiceField(choices=[], label='Squad')
    tag = forms.CharField(max_length=50)
    proc_name = forms.CharField(max_length=50)
    size = forms.IntegerField()
    pool = forms.CharField(max_length=50, required=False)
    active = forms.BooleanField(initial=True)

    def __init__(self, data, *args, **kwargs):
        super(SwarmForm, self).__init__(data, *args, **kwargs)
        self.fields['recipe_id'].choices = [(p.id, p) for p in
                                            models.ConfigRecipe.objects.all()]
        self.fields['squad_id'].choices = [(s.id, s) for s in
                                            models.Squad.objects.all()]

    class Media:
        js = ('js/dash_preview_recipe.js', )
