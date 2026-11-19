from itertools import islice
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from faker import Faker

from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


BATCH_SIZE = 2000


def bulk_insert(model, objects, collect_ids=False):
    """Не держим миллионы объектов в памяти: создаём их партиями."""
    iterator = iter(objects)
    ids = []
    while batch := list(islice(iterator, BATCH_SIZE)):
        created = model.objects.bulk_create(batch, batch_size=BATCH_SIZE)
        if collect_ids:
            ids.extend(obj.pk for obj in created)
    return ids


def rating_for(index, total_likes, total_objects):
    return total_likes // total_objects + (index < total_likes % total_objects)


class Command(BaseCommand):
    help = "Добавить тестовые данные: fill_db ratio (целое число не меньше 2)."

    def add_arguments(self, parser):
        parser.add_argument("ratio", type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        ratio = options["ratio"]
        if ratio < 2:
            raise CommandError(
                "ratio должен быть не меньше 2: для одного пользователя недостаточно "
                "уникальных пар, чтобы создать 200 лайков."
            )

        fake = Faker("ru_RU")
        prefix = uuid4().hex[:16]
        User = get_user_model()
        question_count = ratio * 10
        answer_count = ratio * 100
        question_likes = min(ratio * 100, ratio * question_count)
        answer_likes = ratio * 200 - question_likes

        users = bulk_insert(User, (
            User(
                username=f"demo_{prefix}_{i}",
                email=f"demo_{prefix}_{i}@example.com",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                password="!",  # Непригодный пароль, эти аккаунты только для тестовых данных.
            ) for i in range(ratio)
        ), collect_ids=True)
        bulk_insert(Profile, (Profile(user_id=user_id) for user_id in users))
        tags = bulk_insert(Tag, (
            Tag(name=f"{fake.word()}-{prefix}-{i}") for i in range(ratio)
        ), collect_ids=True)
        self.stdout.write(f"Пользователи и теги: по {ratio}.")

        questions = bulk_insert(Question, (
            Question(
                title=fake.sentence(nb_words=7)[:255],
                text=fake.text(max_nb_chars=300),
                author_id=users[i % ratio],
                rating=rating_for(i, question_likes, question_count),
            ) for i in range(question_count)
        ), collect_ids=True)
        bulk_insert(Question.tags.through, (
            Question.tags.through(question_id=question_id, tag_id=tags[i % ratio])
            for i, question_id in enumerate(questions)
        ))
        self.stdout.write(f"Вопросы: {question_count}.")

        answers = bulk_insert(Answer, (
            Answer(
                text=fake.sentence(nb_words=15),
                author_id=users[i % ratio],
                question_id=questions[i % question_count],
                rating=rating_for(i, answer_likes, answer_count),
            ) for i in range(answer_count)
        ), collect_ids=True)
        self.stdout.write(f"Ответы: {answer_count}.")

        # Сначала проходим все объекты, затем берём следующего пользователя.
        # Поэтому каждая пара (пользователь, объект) встречается ровно один раз.
        bulk_insert(QuestionLike, (
            QuestionLike(user_id=users[i // question_count], question_id=questions[i % question_count])
            for i in range(question_likes)
        ))
        bulk_insert(AnswerLike, (
            AnswerLike(user_id=users[i // answer_count], answer_id=answers[i % answer_count])
            for i in range(answer_likes)
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Добавлено {question_likes + answer_likes} лайков. Заполнение завершено."
        ))
