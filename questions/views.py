from django.http import Http404
from django.shortcuts import redirect, render

from core.pagination import paginate


QUESTIONS = [
    {
        "id": 1,
        "title": "Когда сдать ДЗ?",
        "text": "Не могу найти дедлайн.",
        "rating": 5,
        "tags": ["ДЗ", "Учёба"],
    },
    {
        "id": 2,
        "title": "Как подключить Django?",
        "text": "Создал проект, что дальше?",
        "rating": 3,
        "tags": ["Python", "Django"],
    },
    {
        "id": 3,
        "title": "Зачем нужны шаблоны?",
        "text": "Хочу разобраться с include.",
        "rating": 7,
        "tags": ["Django", "HTML"],
    },
]


# Дополнительные данные-заглушки, чтобы проверить несколько страниц.
for question_id in range(4, 31):
    QUESTIONS.append({
        "id": question_id,
        "title": f"Учебный вопрос №{question_id}",
        "text": f"Описание учебного вопроса №{question_id}.",
        "rating": question_id % 10,
        "tags": ["Django", "Учёба"],
    })


def index(request):
    page = paginate(QUESTIONS, request)
    return render(
        request,
        "questions/index.html",
        {"questions": page, "page_obj": page},
    )


def question_detail(request, question_id):
    for question in QUESTIONS:
        if question["id"] == question_id:
            break
    else:
        raise Http404("Вопрос не найден")

    answers = [
        {"text": "Попробуй посмотреть материалы семинара.", "rating": 5},
        {"text": "Можно уточнить у преподавателя.", "rating": 2},
    ]

    answers.extend(
        {"text": f"Учебный ответ №{number}.", "rating": number % 5}
        for number in range(3, 24)
    )
    page = paginate(answers, request)

    return render(
        request,
        "questions/question.html",
        {"question": question, "answers": page, "page_obj": page},
    )


def hot(request):
    questions = sorted(QUESTIONS, key=lambda question: question["rating"], reverse=True)
    page = paginate(questions, request)
    return render(request, "questions/hot.html", {"questions": page, "page_obj": page})


def tag(request, tag_name):
    questions = [question for question in QUESTIONS if tag_name in question["tags"]]
    page = paginate(questions, request)
    return render(
        request,
        "questions/tag.html",
        {"questions": page, "page_obj": page, "tag_name": tag_name},
    )


def ask(request):
    if request.COOKIES.get("demo_user") != "1":
        return redirect("core:login")
    return render(request, "questions/ask.html")
