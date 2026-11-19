from django.shortcuts import get_object_or_404, redirect, render

from core.pagination import paginate
from .models import Answer, Question, Tag


def index(request):
    page = paginate(Question.objects.new(), request)
    return render(request, "questions/index.html", {"questions": page, "page_obj": page})


def hot(request):
    page = paginate(Question.objects.hot(), request)
    return render(request, "questions/hot.html", {"questions": page, "page_obj": page})


def tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    page = paginate(Question.objects.by_tag(tag), request)
    return render(request, "questions/tag.html", {
        "questions": page, "page_obj": page, "tag_name": tag.name,
    })


def question_detail(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    page = paginate(Answer.objects.for_question(question), request)
    return render(request, "questions/question.html", {
        "question": question, "answers": page, "page_obj": page,
    })


def ask(request):
    if request.COOKIES.get("demo_user") != "1":
        return redirect("core:login")
    return render(request, "questions/ask.html")
