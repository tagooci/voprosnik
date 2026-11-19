from django.conf import settings
from django.db import models
from django.urls import reverse

from .managers import AnswerManager, QuestionManager


class Tag(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("questions:tag", kwargs={"tag_name": self.name})


class Question(models.Model):
    objects = QuestionManager()

    title = models.CharField("Заголовок", max_length=255)
    text = models.TextField("Текст")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Автор",
    )
    tags = models.ManyToManyField(
        Tag, related_name="questions", verbose_name="Теги", blank=True
    )
    rating = models.IntegerField("Рейтинг", default=0)

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ["-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("questions:detail", kwargs={"question_id": self.pk})


class Answer(models.Model):
    objects = AnswerManager()

    text = models.TextField("Текст")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Автор",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Вопрос",
    )
    rating = models.IntegerField("Рейтинг", default=0)

    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
        ordering = ["id"]

    def __str__(self):
        return self.text[:80]


class QuestionLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_likes",
        verbose_name="Пользователь",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="Вопрос",
    )

    class Meta:
        verbose_name = "Лайк вопроса"
        verbose_name_plural = "Лайки вопросов"
        unique_together = [("user", "question")]

    def __str__(self):
        return f"Лайк пользователя {self.user_id} к вопросу {self.question_id}"


class AnswerLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answer_likes",
        verbose_name="Пользователь",
    )
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="Ответ",
    )

    class Meta:
        verbose_name = "Лайк ответа"
        verbose_name_plural = "Лайки ответов"
        unique_together = [("user", "answer")]

    def __str__(self):
        return f"Лайк пользователя {self.user_id} к ответу {self.answer_id}"
