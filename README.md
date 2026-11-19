Нужны Python 3.14 и запущенный Docker Desktop.
Команды выполняются из папки с manage.py.

Перед первым запуском:
cp .env.example .env.local
cp .env.example .env.docker
В обоих файлах замените SECRET_KEY и DB_PASSWORD своими значениями.
DB_NAME, DB_USER и DB_PASSWORD должны совпадать в обоих файлах.
В .env.local оставьте DB_HOST=127.0.0.1, в .env.docker укажите DB_HOST=db.
Файлы .env.local и .env.docker не добавляются в Git.

Локальный запуск Django с PostgreSQL в Docker:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose --env-file .env.docker up -d --wait db
python manage.py migrate
python manage.py runserver

Запуск всего проекта через Docker:
docker compose --env-file .env.docker up --build -d
docker compose --env-file .env.docker exec web python manage.py migrate

Создать администратора локально:
python manage.py createsuperuser
Через Docker:
docker compose --env-file .env.docker exec web python manage.py createsuperuser
Админка: http://localhost:8000/admin/

Заполнить БД локально:
python manage.py fill_db 10
Для большого объёма: python manage.py fill_db 10000
ratio задаёт число пользователей и тегов; вопросов добавляется ratio * 10,
ответов ratio * 100, лайков ratio * 200. Минимальный ratio — 2.
Каждый запуск добавляет данные, существующие записи не удаляются.
Через Docker:
docker compose --env-file .env.docker exec web python manage.py fill_db 10

Проверки:
python manage.py test --noinput
Панель SQL доступна локально при DEBUG=True; при DEBUG=False отключена.

Сайт: http://localhost:8000/
Логи: docker compose --env-file .env.docker logs -f web
Остановка контейнеров: docker compose --env-file .env.docker down
Порты 8000 и 5432 должны быть свободны.
Код подключён из текущей папки; после изменения зависимостей пересоберите образ.
Тома media и postgres_data сохраняют файлы и БД после down.
Вход демонстрационный, без проверки пароля. Формы пока не сохраняют данные.
