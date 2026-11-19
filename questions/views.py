from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from core.pagination import paginate
from .forms import AnswerForm, AnswerVoteForm, CorrectAnswerForm, QuestionForm, QuestionVoteForm
from .models import Answer, Question, Tag


def index(request):
    page = paginate(Question.objects.new().with_user_vote(request.user), request)
    return render(request, "questions/index.html", {"questions": page, "page_obj": page})


def hot(request):
    page = paginate(Question.objects.hot().with_user_vote(request.user), request)
    return render(request, "questions/hot.html", {"questions": page, "page_obj": page})


def tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    page = paginate(Question.objects.by_tag(tag).with_user_vote(request.user), request)
    return render(request, "questions/tag.html", {
        "questions": page, "page_obj": page, "tag_name": tag.name,
    })


@require_http_methods(["GET", "POST"])
def question_detail(request, question_id):
    question = get_object_or_404(Question.objects.with_user_vote(request.user), pk=question_id)
    if request.method == "POST" and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    form = AnswerForm(request.POST if request.method == "POST" else None, user=request.user, question=question)
    if request.method == "POST" and form.is_valid():
        return redirect(form.save())
    page = paginate(Answer.objects.for_question(question).with_user_vote(request.user), request)
    return render(request, "questions/question.html", {
        "question": question, "answers": page, "page_obj": page, "form": form,
    })


@login_required
@require_http_methods(["GET", "POST"])
def ask(request):
    form = QuestionForm(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST" and form.is_valid():
        return redirect(form.save())
    return render(request, "questions/ask.html", {"form": form})


def _ajax_form_response(request, form_class):
    if request.method != "POST":
        response = JsonResponse({"error": "Разрешён только POST."}, status=405)
        response["Allow"] = "POST"
        return response
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Войдите, чтобы выполнить действие.", "login_url": reverse("core:login")}, status=401)
    form = form_class(request.POST, user=request.user)
    if form.is_valid():
        try:
            return JsonResponse(form.save())
        except ValidationError as error:
            form.add_error(None, error)
    codes = {error.code for errors in form.errors.as_data().values() for error in errors}
    status = 403 if "forbidden" in codes else 404 if "not_found" in codes else 409 if "duplicate" in codes else 400
    return JsonResponse({"errors": form.errors.get_json_data()}, status=status)


def question_vote(request):
    return _ajax_form_response(request, QuestionVoteForm)


def answer_vote(request):
    return _ajax_form_response(request, AnswerVoteForm)


def correct_answer(request):
    return _ajax_form_response(request, CorrectAnswerForm)
