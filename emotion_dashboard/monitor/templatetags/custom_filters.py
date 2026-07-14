from django import template


register = template.Library()


@register.filter
def get_item(
    dictionary,
    key,
):
    return dictionary.get(
        key,
        0,
    )


@register.filter
def elided_page_range(page):
    return (
        page.paginator
        .get_elided_page_range(
            page.number
        )
    )