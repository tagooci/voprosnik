from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from core.forms import BootstrapFormMixin
from .models import Answer, AnswerLike, Question, QuestionLike, Tag


class QuestionForm(BootstrapFormMixin, forms.ModelForm):
    tags = forms.CharField(label="Теги", help_text="Через запятую, каждый до 100 символов.", required=False)

    class Meta:
        model = Question
        fields = ("title", "text", "tags")
        widgets = {"text": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_tags(self):
        names = list(dict.fromkeys(name.strip() for name in self.cleaned_data["tags"].split(",") if name.strip()))
        if any(len(name) > 100 or "/" in name for name in names):
            raise forms.ValidationError("Тег должен содержать до 100 символов и не содержать /.")
        return names

    @transaction.atomic
    def save(self, commit=True):
        question = super().save(commit=False)
        question.author = self.user
        if commit:
            question.save()
            tags = [Tag.objects.get_or_create(name=name)[0] for name in self.cleaned_data["tags"]]
            question.tags.set(tags)
        return question


class AnswerForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Answer
        fields = ("text",)
        labels = {"text": "Ваш ответ"}
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, user, question, **kwargs):
        self.user, self.question = user, question
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        answer = super().save(commit=False)
        answer.author, answer.question = self.user, self.question
        if commit:
            answer.save()
        return answer


class VoteForm(forms.Form):
    object_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    value = forms.TypedChoiceField(choices=[(1, "Лайк"), (-1, "Дизлайк")], coerce=int)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if "object_id" not in data or "value" not in data:
            return data
        self.target = self.target_model.objects.filter(pk=data["object_id"]).first()
        if self.target is None:
            raise ValidationError("Объект не найден.", code="not_found")
        self.lookup = {"user": self.user, self.target_field: self.target}
        if self.vote_model.objects.filter(**self.lookup, value=data["value"]).exists():
            raise ValidationError("Вы уже поставили эту оценку.", code="duplicate")
        return data

    @transaction.atomic
    def save(self):
        # Блокируем объект: параллельные голоса не теряют обновления рейтинга.
        target = self.target_model.objects.select_for_update(of=("self",)).get(pk=self.target.pk)
        vote = self.vote_model.objects.filter(**self.lookup).first()
        value = self.cleaned_data["value"]
        if vote and vote.value == value:
            raise ValidationError("Вы уже поставили эту оценку.", code="duplicate")
        previous = vote.value if vote else 0
        if vote:
            vote.value = value
            vote.save(update_fields=["value"])
        else:
            self.vote_model.objects.create(**self.lookup, value=value)
        self.target_model.objects.filter(pk=target.pk).update(rating=F("rating") + value - previous)
        target.refresh_from_db(fields=["rating"])
        return {"rating": target.rating, "value": value}


class QuestionVoteForm(VoteForm):
    target_model, vote_model, target_field = Question, QuestionLike, "question"


class AnswerVoteForm(VoteForm):
    target_model, vote_model, target_field = Answer, AnswerLike, "answer"


class CorrectAnswerForm(forms.Form):
    question_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    answer_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if "question_id" not in data or "answer_id" not in data:
            return data
        self.question = Question.objects.filter(pk=data["question_id"]).first()
        if self.question is None:
            raise ValidationError("Вопрос не найден.", code="not_found")
        if self.question.author_id != self.user.pk:
            raise ValidationError("Выбрать правильный ответ может только автор вопроса.", code="forbidden")
        self.answer = Answer.objects.filter(pk=data["answer_id"], question=self.question).first()
        if self.answer is None:
            raise ValidationError("Ответ не принадлежит этому вопросу.", code="not_found")
        return data

    @transaction.atomic
    def save(self):
        Question.objects.select_for_update(of=("self",)).get(pk=self.question.pk)
        Answer.objects.filter(question=self.question, is_correct=True).update(is_correct=False)
        Answer.objects.filter(pk=self.answer.pk).update(is_correct=True)
        return {"question_id": self.question.pk, "answer_id": self.answer.pk}
