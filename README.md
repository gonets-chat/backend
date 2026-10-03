# OpenVerse backend

Все команды выполняются из каталога `backend`.

## Установка

~~~powershell
poetry install
~~~

## Запуск API

~~~powershell
poetry run uvicorn main:app --app-dir src --host 0.0.0.0 --reload --port 8000
~~~

## Запуск Taskiq worker

~~~powershell
poetry run taskiq worker --app-dir src workers.taskiq.tasks:broker
~~~

## Миграции

Создать миграцию:

~~~powershell
poetry run alembic revision --autogenerate -m "add user names"
~~~

Проверить состояние миграций:

~~~powershell
poetry run alembic current
poetry run alembic heads
~~~

Применить миграции:

~~~powershell
poetry run alembic upgrade head
~~~

## Тесты

~~~powershell
poetry run pytest
~~~
