from django.db import models
from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce


class QuestionQuerySet(models.QuerySet):
    def with_user_vote(self, user):
        from .models import QuestionLike
        if not user.is_authenticated:
            return self.annotate(user_vote=Value(0))
        votes = QuestionLike.objects.filter(user=user, question_id=OuterRef("pk"))
        return self.annotate(user_vote=Coalesce(Subquery(votes.values("value")[:1]), Value(0), output_field=models.IntegerField()))


class QuestionManager(models.Manager.from_queryset(QuestionQuerySet)):
    def get_queryset(self):
        return super().get_queryset().select_related("author__profile").prefetch_related("tags")

    def new(self):
        return self.get_queryset().order_by("-id")

    def hot(self):
        return self.get_queryset().order_by("-rating", "-id")

    def by_tag(self, tag):
        return self.new().filter(tags=tag)


class AnswerQuerySet(models.QuerySet):
    def with_user_vote(self, user):
        from .models import AnswerLike
        if not user.is_authenticated:
            return self.annotate(user_vote=Value(0))
        votes = AnswerLike.objects.filter(user=user, answer_id=OuterRef("pk"))
        return self.annotate(user_vote=Coalesce(Subquery(votes.values("value")[:1]), Value(0), output_field=models.IntegerField()))


class AnswerManager(models.Manager.from_queryset(AnswerQuerySet)):
    def for_question(self, question):
        return self.get_queryset().filter(question=question).select_related("author__profile").order_by("id")
