from django import template

register = template.Library()

# This custom Django template filter is to make it easy to take the dots out of
# hostnames when rendering the dashboard, which is necessary in order to be
# able to use them as class names for the isotope filtering.
@register.filter()
def stripchar(value, arg):
    return value.replace(arg, "")

