from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    max_num = 1


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class UserWithProfileAdmin(UserAdmin):
    inlines = [ProfileInline]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "avatar")
    search_fields = ("user__username", "user__email")
    list_filter = ("user__is_active", ("avatar", admin.EmptyFieldListFilter))
    raw_id_fields = ("user",)
    list_select_related = ("user",)
