from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("api/questions/vote/", views.question_vote, name="question_vote"),
    path("api/answers/vote/", views.answer_vote, name="answer_vote"),
    path("api/answers/correct/", views.correct_answer, name="correct_answer"),
    path("ask/", views.ask, name="ask"),
    path("", views.index, name="index"),
    path("hot/", views.hot, name="hot"),
    path("tag/<str:tag_name>/", views.tag, name="tag"),
    path("question/<int:question_id>/", views.question_detail, name="detail"),
]
