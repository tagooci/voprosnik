from django.db import models


class QuestionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("author").prefetch_related("tags")

    def new(self):
        return self.get_queryset().order_by("-id")

    def hot(self):
        return self.get_queryset().order_by("-rating", "-id")

    def by_tag(self, tag):
        return self.new().filter(tags=tag)


class AnswerManager(models.Manager):
    def for_question(self, question):
        return self.get_queryset().filter(question=question).select_related("author").order_by("id")
