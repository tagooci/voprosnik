Нужен Python 3.14 или Docker Desktop с Docker Compose.
Команды выполняются из папки с manage.py.

Локальный запуск:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Запуск через Docker (Docker Desktop должен быть запущен):
docker compose up --build

Сайт: http://localhost:8000/
Остановка: Ctrl+C, затем docker compose down
Порт 8000 должен быть свободен.
Код подключён из текущей папки; после изменения зависимостей повторите запуск с --build.
Загруженные файлы хранятся в томе media и сохраняются после docker compose down.
Вход демонстрационный, без проверки пароля. Формы пока не сохраняют данные.
