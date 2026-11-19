from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.forms.models import BaseInlineFormSet

from .models import Answer, AnswerLike, Question, QuestionLike, Tag


class CachedAuthorWidget(ForeignKeyRawIdWidget):
    """Используем уже загруженного автора вместо запроса для подписи ID."""

    def label_and_url_for_value(self, value):
        author = getattr(self, "cached_author", None)
        if author is not None and str(author.pk) == str(value):
            return str(author), ""
        return super().label_and_url_for_value(value)


class AnswerInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        widget = form.fields["author"].widget
        cached_widget = CachedAuthorWidget(
            widget.rel, widget.admin_site, attrs=widget.attrs, using=widget.db
        )
        cached_widget.cached_author = form.instance._state.fields_cache.get("author")
        form.fields["author"].widget = cached_widget


class AnswerInline(admin.TabularInline):
    model = Answer
    formset = AnswerInlineFormSet
    fields = ("text", "author", "rating")
    raw_id_fields = ("author",)
    extra = 0
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    list_filter = (("name", admin.EmptyFieldListFilter),)
    ordering = ("name",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "rating")
    search_fields = ("title", "text", "author__username")
    list_filter = ("rating",)
    raw_id_fields = ("author", "tags")
    list_select_related = ("author",)
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question", "author", "rating")
    search_fields = ("text", "question__title", "author__username")
    list_filter = ("rating",)
    raw_id_fields = ("author", "question")
    list_select_related = ("author", "question")


@admin.register(QuestionLike)
class QuestionLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question")
    search_fields = ("user__username", "question__title")
    list_filter = ("user__is_active",)
    raw_id_fields = ("user", "question")
    list_select_related = ("user", "question")


@admin.register(AnswerLike)
class AnswerLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "answer")
    search_fields = ("user__username", "answer__text")
    list_filter = ("user__is_active",)
    raw_id_fields = ("user", "answer")
    list_select_related = ("user", "answer")
