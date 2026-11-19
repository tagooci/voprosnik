from .models import Tag


def sidebar(request):
    return {
        "sidebar_tags": Tag.objects.order_by("name")[:10],
    }