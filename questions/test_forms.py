from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings

from .models import Answer, AnswerLike, Question, QuestionLike, Tag


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ContentFormsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="owner", password="test-pass")
        cls.other = get_user_model().objects.create_user(username="other", password="test-pass")
        cls.question = Question.objects.create(title="Вопрос", text="Текст", author=cls.owner)
        cls.answer = Answer.objects.create(text="Ответ", author=cls.other, question=cls.question)

    def test_question_form_creates_author_and_tags(self):
        self.client.force_login(self.owner)
        response = self.client.post("/ask/", {"title": "Новый вопрос", "text": "Описание", "tags": "Django, Python, Django", "author": self.other.pk})
        question = Question.objects.get(title="Новый вопрос")
        self.assertRedirects(response, question.get_absolute_url())
        self.assertEqual(question.author, self.owner)
        self.assertEqual(set(question.tags.values_list("name", flat=True)), {"Django", "Python"})

    def test_question_invalid_fields_and_tags_preserve_input(self):
        self.client.force_login(self.owner)
        for tags in ["x"*101, "bad/tag"]:
            response = self.client.post("/ask/", {"title": "Сохранённый заголовок", "text": "Описание", "tags": tags})
            self.assertIn("tags", response.context["form"].errors)
            self.assertContains(response, 'value="Сохранённый заголовок"')
        response = self.client.post("/ask/", {"title": "   ", "text": "   ", "tags": ""})
        self.assertIn("title", response.context["form"].errors)
        self.assertIn("text", response.context["form"].errors)
        self.assertEqual(Question.objects.count(), 1)

    def test_answer_redirects_to_page_and_anchor(self):
        Answer.objects.bulk_create([Answer(text=f"Ответ {i}", question=self.question, author=self.other) for i in range(9)])
        self.client.force_login(self.owner)
        response = self.client.post(self.question.get_absolute_url(), {"text": "Мой новый ответ", "author": self.other.pk})
        answer = Answer.objects.get(text="Мой новый ответ")
        self.assertEqual(answer.author, self.owner)
        self.assertEqual(response.url, f"{self.question.get_absolute_url()}?page=2#answer-{answer.pk}")
        page = self.client.get(response.url)
        self.assertContains(page, f'id="answer-{answer.pk}"')
        self.assertContains(page, "Мой новый ответ")

    def test_answer_requires_login_and_nonempty_text(self):
        response = self.client.post(self.question.get_absolute_url(), {"text": "Посторонний"})
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.owner)
        response = self.client.post(self.question.get_absolute_url(), {"text": "   "})
        self.assertIn("text", response.context["form"].errors)
        self.assertEqual(Answer.objects.count(), 1)

    def test_guest_controls_are_disabled_and_have_hints(self):
        response = self.client.get(self.question.get_absolute_url())
        self.assertContains(response, 'disabled title="Войдите, чтобы поставить оценку"')
        self.assertContains(response, 'disabled title="Войдите, чтобы написать ответ"')
        self.assertNotContains(response, "data-correct-form")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.question.get_absolute_url()), "data-correct-form")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.question.get_absolute_url()), "data-correct-form")

    def test_repeated_vote_button_disabled_after_reload(self):
        QuestionLike.objects.create(user=self.other, question=self.question, value=1)
        self.client.force_login(self.other)
        response = self.client.get(self.question.get_absolute_url())
        self.assertContains(response, 'disabled title="Вы уже поставили лайк"')


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AjaxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="author", password="test-pass")
        cls.other = get_user_model().objects.create_user(username="voter", password="test-pass")
        cls.question = Question.objects.create(title="Вопрос", text="Текст", author=cls.owner)
        cls.answer = Answer.objects.create(text="Ответ", question=cls.question, author=cls.other)
        cls.second = Answer.objects.create(text="Второй ответ", question=cls.question, author=cls.owner)

    def test_vote_switch_and_duplicate_for_both_models(self):
        self.client.force_login(self.other)
        for endpoint, obj, model, field in [
            ("/api/questions/vote/", self.question, QuestionLike, "question"),
            ("/api/answers/vote/", self.answer, AnswerLike, "answer"),
        ]:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, {"object_id": obj.pk, "value": 1})
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json(), {"rating": 1, "value": 1})
                self.assertEqual(self.client.post(endpoint, {"object_id": obj.pk, "value": 1}).status_code, 409)
                self.assertEqual(self.client.post(endpoint, {"object_id": obj.pk, "value": -1}).json(), {"rating": -1, "value": -1})
                self.assertEqual(model.objects.filter(user=self.other, **{field: obj}).count(), 1)
                obj.refresh_from_db()
                self.assertEqual(obj.rating, -1)

    def test_votes_require_auth_and_valid_parameters(self):
        for endpoint in ["/api/questions/vote/", "/api/answers/vote/"]:
            self.assertEqual(self.client.post(endpoint, {}).status_code, 401)
            self.assertEqual(self.client.get(endpoint).status_code, 405)
        self.client.force_login(self.other)
        for data in [{}, {"object_id": "abc", "value": 1}, {"object_id": self.question.pk, "value": 0}, {"object_id": 10**100, "value": 1}]:
            self.assertEqual(self.client.post("/api/questions/vote/", data).status_code, 400)
        self.assertEqual(self.client.post("/api/questions/vote/", {"object_id": 999999, "value": 1}).status_code, 404)

    def test_only_owner_can_choose_correct_answer(self):
        self.client.force_login(self.other)
        data = {"question_id": self.question.pk, "answer_id": self.answer.pk}
        self.assertEqual(self.client.post("/api/answers/correct/", data).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post("/api/answers/correct/", data).status_code, 200)
        self.answer.refresh_from_db()
        self.assertTrue(self.answer.is_correct)
        data["answer_id"] = self.second.pk
        self.assertEqual(self.client.post("/api/answers/correct/", data).status_code, 200)
        self.answer.refresh_from_db(); self.second.refresh_from_db()
        self.assertFalse(self.answer.is_correct)
        self.assertTrue(self.second.is_correct)

    def test_correct_answer_auth_method_validation_and_wrong_question(self):
        self.assertEqual(self.client.get("/api/answers/correct/").status_code, 405)
        self.assertEqual(self.client.post("/api/answers/correct/", {}).status_code, 401)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post("/api/answers/correct/", {}).status_code, 400)
        different = Question.objects.create(title="Другой", text="Текст", author=self.owner)
        response = self.client.post("/api/answers/correct/", {"question_id": different.pk, "answer_id": self.answer.pk})
        self.assertEqual(response.status_code, 404)

    def test_csrf_required_and_valid_token_works(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for endpoint in ["/api/questions/vote/", "/api/answers/vote/", "/api/answers/correct/"]:
            response = client.post(endpoint, {})
            self.assertEqual(response.status_code, 403)
            self.assertIn("CSRF", response.json()["error"])
        client.get(self.question.get_absolute_url())
        token = client.cookies["csrftoken"].value
        response = client.post("/api/questions/vote/", {"object_id": self.question.pk, "value": 1}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_database_constraints(self):
        QuestionLike.objects.create(user=self.owner, question=self.question)
        with self.assertRaises(IntegrityError), transaction.atomic():
            QuestionLike.objects.create(user=self.owner, question=self.question)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AnswerLike.objects.create(user=self.owner, answer=self.answer, value=0)
        self.answer.is_correct = True
        self.answer.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.second.is_correct = True
            self.second.save()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConcurrentVotingTests(TransactionTestCase):
    def test_parallel_votes_do_not_lose_rating_updates(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from .forms import QuestionVoteForm

        users = [get_user_model().objects.create_user(username=f"parallel_{i}") for i in range(2)]
        question = Question.objects.create(title="Параллельные голоса", text="Текст", author=users[0])
        ready = Barrier(2)

        def vote(user):
            try:
                form = QuestionVoteForm({"object_id": question.pk, "value": 1}, user=user)
                if not form.is_valid():
                    raise AssertionError(form.errors)
                ready.wait(timeout=10)
                return form.save()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(vote, users))
        question.refresh_from_db()
        self.assertEqual(question.rating, 2)
        self.assertEqual(QuestionLike.objects.filter(question=question).count(), 2)
