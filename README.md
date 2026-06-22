# База правовой аналитики

Учебный проект — Тема №5, Цифровая кафедра ДГТУ.

База знаний по праву РФ: нормы законодательства, судебная практика, правовые заключения с полнотекстовым поиском, фасетными фильтрами, графом связей и конструктором заключений.

## Стек

- **Backend:** Django 5.1, Python 3.12, PostgreSQL 16
- **Поиск:** PostgreSQL FTS (русский словарь, GIN-индекс, SearchRank)
- **Frontend:** Bootstrap 5, HTMX, Chart.js, vis-network
- **Прочее:** django-taggit, django-filter, docxtpl, WhiteNoise, Docker Compose

## Быстрый старт

```bash
# 1. Скопировать переменные окружения
cp .env.example .env
# Отредактировать .env: задать SECRET_KEY

# 2. Запустить
docker compose up --build

# Приложение: http://localhost:8000
# Админка:    http://localhost:8000/admin/
```

При первом запуске автоматически:
- применяются миграции
- загружаются демо-данные (`python manage.py load_legal_data`)
- собирается статика

## Структура проекта

```
apps/
  catalog/    — отрасли права (LegalBranch)
  knowledge/  — нормы (Norm), практика (CourtCase), заключения (LegalOpinion)
  search/     — полнотекстовый и фасетный поиск
  builder/    — конструктор правового заключения (.docx экспорт)
  analytics/  — дашборд (Chart.js)
  accounts/   — аутентификация, роли
data/         — JSON-файлы с контентом для load_legal_data
word_templates/ — .docx шаблон заключения
tests/        — pytest-тесты
```

## Роли

| Роль | Возможности |
|---|---|
| Редактор базы | Добавление/редактирование норм, практики, тегов |
| Аналитик | Поиск, построение заключений, дашборд |
| Читатель | Поиск и просмотр |

## Разработка (без Docker)

```bash
pip install -r requirements.txt

# SQLite для локальной отладки
export DATABASE_URL=sqlite:///db.sqlite3
export SECRET_KEY=dev-key
export DEBUG=True

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Тесты

```bash
pytest
```

## Этапы реализации

- [x] Этап 1: Каркас + Docker
- [x] Этап 2: Модели данных + миграции
- [x] Этап 3: Наполнение базы (10 отраслей, 28 норм, 17 решений, 8 заключений)
- [x] Этап 4: Полнотекстовый поиск (FTS, GIN-индекс, русский словарь, HTMX)
- [x] Этап 5: Фасетный поиск + HTMX (отрасль/тег/дата, счётчики, chips)
- [x] Этап 6: Карточки + граф связей (vis-network, JSON API, списки)
- [x] Этап 7: Конструктор заключений (сессионная корзина, форма, .docx экспорт)
- [x] Этап 8: Дашборд аналитики (Chart.js: 4 графика, KPI-карточки)
- [ ] Этап 9: Роли и доступ
- [ ] Этап 10: Стабилизация + fixtures
