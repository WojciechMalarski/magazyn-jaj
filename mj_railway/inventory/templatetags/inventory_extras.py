from django import template

register = template.Library()


@register.filter
def get_item(form, code):
    return form[f'{code}_crates']


@register.filter
def get_item_trays(form, code):
    return form[f'{code}_trays']
