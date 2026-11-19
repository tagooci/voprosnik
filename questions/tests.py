from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.urls import reverse

from .models import Answer, Question, Tag


class QuestionPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = get_user_model().objects.create_user(username="test_author")
        cls.tag = Tag.objects.create(name="Django")
        cls.empty_tag = Tag.objects.create(name="Пустой тег")
        cls.first = Question.objects.create(title="Первый вопрос", text="Текст", author=cls.author, rating=10)
        cls.second = Question.objects.create(title="Второй вопрос", text="Текст", author=cls.author, rating=2)
        cls.first.tags.add(cls.tag)

    def test_ordering(self):
        new = self.client.get(reverse("questions:index"))
        hot = self.client.get(reverse("questions:hot"))
        self.assertEqual([q.pk for q in new.context["questions"]], [self.second.pk, self.first.pk])
        self.assertEqual([q.pk for q in hot.context["questions"]], [self.first.pk, self.second.pk])

    def test_tag_filter_and_empty_state(self):
        response = self.client.get(self.tag.get_absolute_url())
        self.assertEqual([q.pk for q in response.context["questions"]], [self.first.pk])
        self.assertContains(self.client.get(self.empty_tag.get_absolute_url()), "Вопросов с этим тегом пока нет.")

    def test_missing_objects(self):
        for url in ["/question/999999/", "/question/abc/", "/question/-1/", "/tag/несуществующий/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_empty_questions_and_answers(self):
        self.assertContains(self.client.get(self.first.get_absolute_url()), "Пока нет ни одного ответа")
        Question.objects.all().delete()
        for name in ["questions:index", "questions:hot"]:
            self.assertContains(self.client.get(reverse(name)), "Пока нет ни одного вопроса.")

    def test_pagination(self):
        Question.objects.bulk_create([
            Question(title=f"Вопрос {i}", text="Текст", author=self.author) for i in range(15)
        ])
        Answer.objects.bulk_create([
            Answer(question=self.first, author=self.author, text=f"Ответ {i}") for i in range(15)
        ])
        for url, key in [(reverse("questions:index"), "questions"), (self.first.get_absolute_url(), "answers")]:
            with self.subTest(url=url):
                page = self.client.get(url, {"page": 2}).context[key]
                self.assertEqual(page.number, 2)
                self.assertGreater(len(page), 0)
                for invalid in ["abc", "-1", "0", "999999", "1.5"]:
                    self.assertEqual(self.client.get(url, {"page": invalid}).context[key].number, 1)

    def test_related_objects_do_not_cause_n_plus_one(self):
        # Один запрос для вопросов с авторами, второй — для всех их тегов.
        with self.assertNumQueries(2):
            for question in Question.objects.new():
                str(question.author.username)
                list(question.tags.all())
        Question.objects.bulk_create([
            Question(title=f"Вопрос {i}", text="Текст", author=self.author) for i in range(10)
        ])
        with self.assertNumQueries(2):
            for question in Question.objects.new():
                str(question.author.username)
                list(question.tags.all())
        Answer.objects.bulk_create([
            Answer(question=self.first, author=self.author, text=f"Ответ {i}") for i in range(10)
        ])
        with self.assertNumQueries(1):
            for answer in Answer.objects.for_question(self.first):
                str(answer.author.username)

    def test_rendered_pages_have_constant_query_counts(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        Answer.objects.create(question=self.first, author=self.author, text="Ответ")
        pages = [
            (reverse("questions:index"), 4),
            (reverse("questions:hot"), 4),
            (self.tag.get_absolute_url(), 5),
            (self.first.get_absolute_url(), 5),
        ]
        self.client.get(reverse("questions:index"))
        for url, expected in pages:
            with self.subTest(url=url, size="small"):
                with CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(len(queries), expected)

        questions = Question.objects.bulk_create([
            Question(title=f"Вопрос {i}", text="Текст", author=self.author) for i in range(15)
        ])
        Question.tags.through.objects.bulk_create([
            Question.tags.through(question_id=q.pk, tag_id=self.tag.pk) for q in questions
        ])
        Answer.objects.bulk_create([
            Answer(question=self.first, author=self.author, text=f"Ответ {i}") for i in range(15)
        ])
        for url, expected in pages:
            with self.subTest(url=url, size="larger"):
                with CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(len(queries), expected)


class FillDbTests(TestCase):
    def fill(self, ratio):
        from io import StringIO
        from django.core.management import call_command
        call_command("fill_db", ratio, stdout=StringIO())

    def test_counts_ratings_and_repeat_run(self):
        from django.db.models import Count
        from core.models import Profile
        from .models import AnswerLike, QuestionLike

        self.fill(2)
        self.assertEqual(get_user_model().objects.count(), 2)
        self.assertEqual(Profile.objects.count(), 2)
        self.assertEqual(Tag.objects.count(), 2)
        self.assertEqual(Question.objects.count(), 20)
        self.assertEqual(Question.tags.through.objects.count(), 20)
        self.assertEqual(Answer.objects.count(), 200)
        self.assertEqual(QuestionLike.objects.count() + AnswerLike.objects.count(), 400)
        for model in [Question, Answer]:
            self.assertFalse(model.objects.annotate(actual=Count("likes")).exclude(rating=models.F("actual")).exists())
        self.assertFalse(get_user_model().objects.first().has_usable_password())
        self.fill(2)
        self.assertEqual(get_user_model().objects.count(), 4)
        self.assertEqual(Question.objects.count(), 40)
        self.assertEqual(Answer.objects.count(), 400)
        self.assertEqual(QuestionLike.objects.count() + AnswerLike.objects.count(), 800)

    def test_invalid_ratio_does_not_insert_data(self):
        from django.core.management.base import CommandError
        for ratio in [0, -1, 1]:
            with self.assertRaises(CommandError):
                self.fill(ratio)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_queries_are_batched(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        # Эти объёмы помещаются в одинаковое число партий: запросов не больше
        # при увеличении количества объектов.
        with CaptureQueriesContext(connection) as small:
            self.fill(2)
        with CaptureQueriesContext(connection) as larger:
            self.fill(3)
        self.assertEqual(len(small), len(larger))


class PaginationRangeTests(TestCase):
    def test_large_page_range_is_short_and_keeps_query_parameters(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        from core.pagination import paginate

        request = RequestFactory().get("/", {"page": 5000, "s": "django"})
        page = paginate(range(100100), request)
        self.assertLessEqual(len(page.pagination_range), 11)
        self.assertIn(1, page.pagination_range)
        self.assertIn(5000, page.pagination_range)
        self.assertIn(10010, page.pagination_range)
        self.assertIn(page.paginator.ELLIPSIS, page.pagination_range)
        html = render_to_string("core/partials/pagination.html", {"page_obj": page}, request=request)
        self.assertIn("s=django", html)
        self.assertNotIn("page=%E2%80%A6", html)
