from django import template

register = template.Library()

# Allow rendering formfields with our custom template include by saying 
# {% formfield form.somefield %}
@register.inclusion_tag('_formfield.html')
def formfield(field):
    return {'field': field}

