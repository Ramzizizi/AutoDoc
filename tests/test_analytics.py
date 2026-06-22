import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import LegalBranch
from apps.knowledge.models import Norm, CourtCase, LegalOpinion

User = get_user_model()


class TestDashboard(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='analyst', password='p')
        self.client.login(username='analyst', password='p')

        branch = LegalBranch.objects.create(name='Гражданское', slug='civil-a')
        self.norm = Norm.objects.create(
            title='ГК РФ', norm_type='code', article='ст. 1', text='Текст.', branch=branch,
        )
        self.case = CourtCase.objects.create(
            court='Суд', case_number='А-001/2022',
            decision_date='2022-05-01', thesis='Тезис', branch=branch,
        )
        self.opinion = LegalOpinion.objects.create(
            title='Заключение', text='Текст.', author=self.user,
        )

    def test_dashboard_status(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        assert resp.status_code == 200

    def test_dashboard_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('analytics:dashboard'))
        assert resp.status_code == 302

    def test_dashboard_kpi(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        content = resp.content.decode()
        assert '1' in content  # at least counts appear

    def test_dashboard_context_totals(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        assert resp.context['total_norms'] == 1
        assert resp.context['total_cases'] == 1
        assert resp.context['total_opinions'] == 1
        assert resp.context['total_branches'] >= 1

    def test_dashboard_chart_data_valid_json(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        ctx = resp.context
        for key in ('norms_by_branch_labels', 'norms_by_branch_data',
                    'norms_by_type_labels', 'norms_by_type_data',
                    'cases_by_branch_labels', 'cases_by_branch_data',
                    'cases_by_year_labels', 'cases_by_year_data'):
            parsed = json.loads(ctx[key])
            assert isinstance(parsed, list)

    def test_dashboard_norms_by_branch(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        labels = json.loads(resp.context['norms_by_branch_labels'])
        data = json.loads(resp.context['norms_by_branch_data'])
        assert 'Гражданское' in labels
        assert data[labels.index('Гражданское')] == 1

    def test_dashboard_cases_by_year(self):
        resp = self.client.get(reverse('analytics:dashboard'))
        years = json.loads(resp.context['cases_by_year_labels'])
        counts = json.loads(resp.context['cases_by_year_data'])
        assert '2022' in years
        assert counts[years.index('2022')] == 1
