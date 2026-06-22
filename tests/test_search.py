import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import connection

from apps.catalog.models import LegalBranch
from apps.knowledge.models import Norm, CourtCase, LegalOpinion

User = get_user_model()

IS_POSTGRES = connection.vendor == 'postgresql'
skip_sqlite = pytest.mark.skipif(not IS_POSTGRES, reason='Требуется PostgreSQL для FTS')


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='pass')


@pytest.fixture
def branch(db):
    return LegalBranch.objects.create(name='Гражданское право', slug='civil')


@pytest.fixture
def norm(db, branch):
    return Norm.objects.create(
        title='Гражданский кодекс РФ, ст. 309. Исполнение обязательств',
        norm_type='code',
        article='ст. 309 ГК РФ',
        text='Обязательства должны исполняться надлежащим образом в соответствии с условиями договора.',
        branch=branch,
    )


@pytest.fixture
def court_case(db, branch, norm):
    case = CourtCase.objects.create(
        court='Арбитражный суд Ростовской области',
        case_number='А53-12345/2022',
        decision_date='2022-09-20',
        thesis='Отказ от исполнения договора аренды признан незаконным',
        text='Ответчик прекратил исполнение договора аренды без законных оснований.',
        branch=branch,
    )
    case.related_norms.add(norm)
    return case


class TestSearchView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u', password='p')
        self.client.login(username='u', password='p')

    def test_search_page_loads(self):
        response = self.client.get(reverse('search:search'))
        assert response.status_code == 200

    def test_empty_query_shows_prompt(self):
        response = self.client.get(reverse('search:search'))
        assert 'Введите запрос' in response.content.decode()

    def test_search_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('search:search') + '?q=договор')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_htmx_request_returns_partial(self):
        response = self.client.get(
            reverse('search:search') + '?q=тест',
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200
        assert b'<!DOCTYPE' not in response.content


@pytest.mark.django_db
@skip_sqlite
class TestFTSSearch:
    def test_exact_match(self, client, user, norm):
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q=обязательства')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'ст. 309 ГК РФ' in content or 'Исполнение обязательств' in content

    def test_stemming(self, client, user, norm):
        """Поиск по словоформе 'обязательств' должен найти 'обязательства'."""
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q=обязательств')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'ст. 309' in content

    def test_type_filter_norm(self, client, user, norm, court_case):
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q=исполнение&type=norm')
        content = response.content.decode()
        assert 'Норма права' in content
        assert 'Судебная практика' not in content

    def test_type_filter_case(self, client, user, norm, court_case):
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q=аренда&type=case')
        content = response.content.decode()
        assert 'Судебная практика' in content

    def test_no_results(self, client, user):
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q=несуществующийзапросxyz')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'ничего не найдено' in content.lower()

    def test_websearch_phrase(self, client, user, norm):
        """Поиск по фразе в кавычках."""
        client.login(username=user.username, password='pass')
        response = client.get(reverse('search:search') + '?q="надлежащим образом"')
        assert response.status_code == 200
        content = response.content.decode()
        assert 'ст. 309' in content
