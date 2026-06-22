import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from apps.catalog.models import LegalBranch
from apps.knowledge.models import Norm, CourtCase, LegalOpinion

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='u2', password='p')


@pytest.fixture
def branch(db):
    return LegalBranch.objects.create(name='Гражданское право', slug='civil-k')


@pytest.fixture
def norm(db, branch):
    return Norm.objects.create(
        title='ГК РФ ст. 309',
        norm_type='code',
        article='ст. 309 ГК РФ',
        text='Обязательства должны исполняться надлежащим образом.',
        branch=branch,
    )


@pytest.fixture
def court_case(db, branch, norm):
    case = CourtCase.objects.create(
        court='Арбитражный суд',
        case_number='А53-001/2023',
        decision_date='2023-01-15',
        thesis='Тест связей',
        branch=branch,
    )
    case.related_norms.add(norm)
    return case


@pytest.fixture
def opinion(db, norm, court_case):
    u = User.objects.create_user(username='author', password='p')
    op = LegalOpinion.objects.create(title='Тестовое заключение', text='Текст заключения.', author=u)
    op.related_norms.add(norm)
    op.related_cases.add(court_case)
    return op


class TestKnowledgeViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='viewer', password='p')
        self.client.login(username='viewer', password='p')
        self.branch = LegalBranch.objects.create(name='Тестовая', slug='test-branch')
        self.norm = Norm.objects.create(
            title='Тестовая норма', norm_type='law',
            article='ст. 1', text='Текст нормы.', branch=self.branch,
        )
        self.case = CourtCase.objects.create(
            court='Тестовый суд', case_number='Т-001/2023',
            decision_date='2023-06-01', thesis='Тезис дела', branch=self.branch,
        )
        self.case.related_norms.add(self.norm)
        self.opinion = LegalOpinion.objects.create(
            title='Заключение', text='Текст.',
            author=self.user, is_public=True,
        )
        self.opinion.related_norms.add(self.norm)
        self.opinion.related_cases.add(self.case)

    # --- список ---

    def test_norm_list(self):
        response = self.client.get(reverse('knowledge:norm_list'))
        assert response.status_code == 200
        assert 'Тестовая норма' in response.content.decode()

    def test_case_list(self):
        response = self.client.get(reverse('knowledge:case_list'))
        assert response.status_code == 200
        assert 'Т-001/2023' in response.content.decode()

    def test_opinion_list(self):
        response = self.client.get(reverse('knowledge:opinion_list'))
        assert response.status_code == 200
        assert 'Заключение' in response.content.decode()

    # --- карточки ---

    def test_norm_detail(self):
        response = self.client.get(reverse('knowledge:norm_detail', args=[self.norm.pk]))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'ст. 1' in content
        assert 'Граф связей' in content

    def test_case_detail(self):
        response = self.client.get(reverse('knowledge:case_detail', args=[self.case.pk]))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Тезис дела' in content
        assert 'Граф связей' in content

    def test_opinion_detail(self):
        response = self.client.get(reverse('knowledge:opinion_detail', args=[self.opinion.pk]))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Заключение' in content
        assert 'Граф связей' in content

    # --- граф API ---

    def test_graph_norm(self):
        response = self.client.get(
            reverse('knowledge:graph_data', args=['norm', self.norm.pk])
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert 'nodes' in data and 'edges' in data
        node_ids = [n['id'] for n in data['nodes']]
        assert f'norm-{self.norm.pk}' in node_ids
        assert f'case-{self.case.pk}' in node_ids

    def test_graph_case(self):
        response = self.client.get(
            reverse('knowledge:graph_data', args=['case', self.case.pk])
        )
        data = json.loads(response.content)
        node_ids = [n['id'] for n in data['nodes']]
        assert f'case-{self.case.pk}' in node_ids
        assert f'norm-{self.norm.pk}' in node_ids

    def test_graph_opinion(self):
        response = self.client.get(
            reverse('knowledge:graph_data', args=['opinion', self.opinion.pk])
        )
        data = json.loads(response.content)
        node_ids = [n['id'] for n in data['nodes']]
        assert f'opinion-{self.opinion.pk}' in node_ids
        assert f'norm-{self.norm.pk}' in node_ids
        assert f'case-{self.case.pk}' in node_ids

    def test_graph_center_node_group(self):
        response = self.client.get(
            reverse('knowledge:graph_data', args=['norm', self.norm.pk])
        )
        data = json.loads(response.content)
        center = next(n for n in data['nodes'] if n['id'] == f'norm-{self.norm.pk}')
        assert center['group'] == 'center'

    def test_lists_require_login(self):
        self.client.logout()
        for url in [
            reverse('knowledge:norm_list'),
            reverse('knowledge:case_list'),
            reverse('knowledge:opinion_list'),
        ]:
            resp = self.client.get(url)
            assert resp.status_code == 302

    def test_reader_sees_only_public_opinions(self):
        private_op = LegalOpinion.objects.create(
            title='Закрытое заключение', text='Текст.', is_public=False,
        )
        resp = self.client.get(reverse('knowledge:opinion_list'))
        content = resp.content.decode()
        assert 'Заключение' in content          # публичное (setUp, is_public=True)
        assert 'Закрытое заключение' not in content

    def test_reader_blocked_from_private_opinion_detail(self):
        private_op = LegalOpinion.objects.create(
            title='Закрытое', text='Текст.', is_public=False,
        )
        resp = self.client.get(reverse('knowledge:opinion_detail', args=[private_op.pk]))
        assert resp.status_code == 404

    def test_analyst_sees_private_opinion(self):
        from django.contrib.auth.models import Group
        from apps.accounts.roles import ROLE_ANALYST
        analyst = User.objects.create_user(username='analyst_k', password='p')
        group, _ = Group.objects.get_or_create(name=ROLE_ANALYST)
        analyst.groups.add(group)
        self.client.force_login(analyst)

        private_op = LegalOpinion.objects.create(
            title='Закрытое', text='Текст.', is_public=False,
        )
        resp = self.client.get(reverse('knowledge:opinion_detail', args=[private_op.pk]))
        assert resp.status_code == 200
