import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncYear

from apps.knowledge.models import Norm, CourtCase, LegalOpinion
from apps.catalog.models import LegalBranch


@login_required
def dashboard(request):
    # ── KPI ──────────────────────────────────────────────────────────────────
    total_norms = Norm.objects.count()
    total_cases = CourtCase.objects.count()
    total_opinions = LegalOpinion.objects.count()
    total_branches = LegalBranch.objects.count()

    # ── Нормы по отраслям ────────────────────────────────────────────────────
    norms_by_branch = list(
        Norm.objects
        .filter(branch__isnull=False)
        .values('branch__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    norms_by_branch_labels = [r['branch__name'] for r in norms_by_branch]
    norms_by_branch_data = [r['count'] for r in norms_by_branch]

    # ── Нормы по типам ───────────────────────────────────────────────────────
    norm_type_map = dict(Norm._meta.get_field('norm_type').choices)  # type → label
    norms_by_type = list(
        Norm.objects
        .values('norm_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    norms_by_type_labels = [norm_type_map.get(r['norm_type'], r['norm_type']) for r in norms_by_type]
    norms_by_type_data = [r['count'] for r in norms_by_type]

    # ── Практика по отраслям ─────────────────────────────────────────────────
    cases_by_branch = list(
        CourtCase.objects
        .filter(branch__isnull=False)
        .values('branch__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    cases_by_branch_labels = [r['branch__name'] for r in cases_by_branch]
    cases_by_branch_data = [r['count'] for r in cases_by_branch]

    # ── Динамика решений по годам ────────────────────────────────────────────
    cases_by_year = list(
        CourtCase.objects
        .annotate(year=TruncYear('decision_date'))
        .values('year')
        .annotate(count=Count('id'))
        .order_by('year')
    )
    cases_by_year_labels = [r['year'].strftime('%Y') for r in cases_by_year if r['year']]
    cases_by_year_data = [r['count'] for r in cases_by_year if r['year']]

    context = {
        'total_norms': total_norms,
        'total_cases': total_cases,
        'total_opinions': total_opinions,
        'total_branches': total_branches,
        # chart data as JSON strings
        'norms_by_branch_labels': json.dumps(norms_by_branch_labels, ensure_ascii=False),
        'norms_by_branch_data': json.dumps(norms_by_branch_data),
        'norms_by_type_labels': json.dumps(norms_by_type_labels, ensure_ascii=False),
        'norms_by_type_data': json.dumps(norms_by_type_data),
        'cases_by_branch_labels': json.dumps(cases_by_branch_labels, ensure_ascii=False),
        'cases_by_branch_data': json.dumps(cases_by_branch_data),
        'cases_by_year_labels': json.dumps(cases_by_year_labels),
        'cases_by_year_data': json.dumps(cases_by_year_data),
    }
    return render(request, 'analytics/dashboard.html', context)
