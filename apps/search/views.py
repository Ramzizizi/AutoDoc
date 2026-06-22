from collections import defaultdict

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.db import connection
from django.urls import reverse

from apps.catalog.models import LegalBranch
from apps.knowledge.models import Norm, CourtCase, LegalOpinion


# ─── helpers ────────────────────────────────────────────────────────────────

def _build_norm_qs(query, is_postgres):
    if is_postgres:
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
        sq = SearchQuery(query, config='russian', search_type='websearch')
        vec = SearchVector('title', 'article', 'text', config='russian')
        return (
            Norm.objects
            .annotate(
                search=vec,
                rank=SearchRank(vec, sq),
                snippet=SearchHeadline('text', sq, config='russian', max_words=40, min_words=20),
            )
            .filter(search=sq)
        )
    return (
        Norm.objects
        .filter(Q(title__icontains=query) | Q(text__icontains=query) | Q(article__icontains=query))
        .annotate(rank=_const(1.0), snippet=_const(''))
    )


def _build_case_qs(query, is_postgres):
    if is_postgres:
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
        sq = SearchQuery(query, config='russian', search_type='websearch')
        vec = SearchVector('case_number', 'thesis', 'text', config='russian')
        return (
            CourtCase.objects
            .annotate(
                search=vec,
                rank=SearchRank(vec, sq),
                snippet=SearchHeadline('thesis', sq, config='russian', max_words=40, min_words=20),
            )
            .filter(search=sq)
        )
    return (
        CourtCase.objects
        .filter(Q(thesis__icontains=query) | Q(text__icontains=query) | Q(case_number__icontains=query))
        .annotate(rank=_const(1.0), snippet=_const(''))
    )


def _build_opinion_qs(query, is_postgres):
    if is_postgres:
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
        sq = SearchQuery(query, config='russian', search_type='websearch')
        vec = SearchVector('title', 'text', config='russian')
        return (
            LegalOpinion.objects
            .annotate(
                search=vec,
                rank=SearchRank(vec, sq),
                snippet=SearchHeadline('text', sq, config='russian', max_words=40, min_words=20),
            )
            .filter(search=sq)
        )
    return (
        LegalOpinion.objects
        .filter(Q(title__icontains=query) | Q(text__icontains=query))
        .annotate(rank=_const(1.0), snippet=_const(''))
    )


def _const(value):
    from django.db.models import Value, FloatField, CharField
    if isinstance(value, float):
        return Value(value, output_field=FloatField())
    return Value(value, output_field=CharField())


def _apply_date_filter(qs, date_from, date_to, field):
    if date_from:
        qs = qs.filter(**{f'{field}__gte': date_from})
    if date_to:
        qs = qs.filter(**{f'{field}__lte': date_to})
    return qs


def _get_branch_facets(query, is_postgres):
    """Подсчёт количества норм и практики по отраслям для текущего запроса."""
    counts = defaultdict(int)

    if is_postgres:
        from django.contrib.postgres.search import SearchVector, SearchQuery
        sq = SearchQuery(query, config='russian', search_type='websearch')
        norm_rows = (
            Norm.objects
            .annotate(search=SearchVector('title', 'article', 'text', config='russian'))
            .filter(search=sq, branch__isnull=False)
            .values('branch__id', 'branch__name').annotate(n=Count('id'))
        )
        case_rows = (
            CourtCase.objects
            .annotate(search=SearchVector('case_number', 'thesis', 'text', config='russian'))
            .filter(search=sq, branch__isnull=False)
            .values('branch__id', 'branch__name').annotate(n=Count('id'))
        )
    else:
        norm_rows = (
            Norm.objects
            .filter(Q(title__icontains=query) | Q(text__icontains=query), branch__isnull=False)
            .values('branch__id', 'branch__name').annotate(n=Count('id'))
        )
        case_rows = (
            CourtCase.objects
            .filter(Q(thesis__icontains=query) | Q(text__icontains=query), branch__isnull=False)
            .values('branch__id', 'branch__name').annotate(n=Count('id'))
        )

    for row in norm_rows:
        counts[(row['branch__id'], row['branch__name'])] += row['n']
    for row in case_rows:
        counts[(row['branch__id'], row['branch__name'])] += row['n']

    return sorted(counts.items(), key=lambda x: -x[1])


def _get_tag_facets(results):
    """Топ-15 тегов из текущих результатов поиска."""
    counts = defaultdict(int)
    for item in results:
        for tag in item['tags']:
            counts[tag] += 1
    return sorted(counts.items(), key=lambda x: -x[1])[:15]


def _norm_to_dict(obj):
    return {
        'type': 'norm', 'type_label': 'Норма права', 'type_color': 'primary',
        'title': obj.title,
        'subtitle': obj.get_norm_type_display(),
        'snippet': getattr(obj, 'snippet', ''),
        'rank': float(getattr(obj, 'rank', 1)),
        'url': reverse('knowledge:norm_detail', args=[obj.pk]),
        'branch': str(obj.branch) if obj.branch else '',
        'branch_id': obj.branch_id,
        'tags': list(obj.tags.names()),
    }


def _case_to_dict(obj):
    return {
        'type': 'case', 'type_label': 'Судебная практика', 'type_color': 'success',
        'title': obj.thesis,
        'subtitle': f'{obj.court} · {obj.decision_date.strftime("%d.%m.%Y")}',
        'snippet': getattr(obj, 'snippet', ''),
        'rank': float(getattr(obj, 'rank', 1)),
        'url': reverse('knowledge:case_detail', args=[obj.pk]),
        'branch': str(obj.branch) if obj.branch else '',
        'branch_id': obj.branch_id,
        'tags': list(obj.tags.names()),
    }


def _opinion_to_dict(obj):
    return {
        'type': 'opinion', 'type_label': 'Правовое заключение', 'type_color': 'warning',
        'title': obj.title,
        'subtitle': f'Автор: {obj.author}' if obj.author else '',
        'snippet': getattr(obj, 'snippet', ''),
        'rank': float(getattr(obj, 'rank', 1)),
        'url': reverse('knowledge:opinion_detail', args=[obj.pk]),
        'branch': '',
        'branch_id': None,
        'tags': list(obj.tags.names()),
    }


# ─── main view ──────────────────────────────────────────────────────────────

@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    record_type = request.GET.get('type', '').strip()
    branch_id = request.GET.get('branch', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    is_postgres = connection.vendor == 'postgresql'
    results = []
    branch_facets = []
    tag_facets = []
    active_branch = None

    if query:
        # — нормы —
        if not record_type or record_type == 'norm':
            norm_qs = _build_norm_qs(query, is_postgres).select_related('branch')
            if branch_id:
                norm_qs = norm_qs.filter(branch_id=branch_id)
            if tag_filter:
                norm_qs = norm_qs.filter(tags__name=tag_filter)
            norm_qs = _apply_date_filter(norm_qs, date_from, date_to, 'effective_date')
            results += [_norm_to_dict(o) for o in norm_qs.order_by('-rank')[:30]]

        # — практика —
        if not record_type or record_type == 'case':
            case_qs = _build_case_qs(query, is_postgres).select_related('branch')
            if branch_id:
                case_qs = case_qs.filter(branch_id=branch_id)
            if tag_filter:
                case_qs = case_qs.filter(tags__name=tag_filter)
            case_qs = _apply_date_filter(case_qs, date_from, date_to, 'decision_date')
            results += [_case_to_dict(o) for o in case_qs.order_by('-rank')[:30]]

        # — заключения (branch-фильтр не применяется, нет поля branch) —
        if not record_type or record_type == 'opinion':
            if not branch_id:
                opinion_qs = _build_opinion_qs(query, is_postgres)
                if tag_filter:
                    opinion_qs = opinion_qs.filter(tags__name=tag_filter)
                results += [_opinion_to_dict(o) for o in opinion_qs.order_by('-rank')[:30]]

        results.sort(key=lambda x: x['rank'], reverse=True)

        # — фасеты (считаем без доп. фильтров, только по тексту) —
        branch_facets = _get_branch_facets(query, is_postgres)
        tag_facets = _get_tag_facets(results)

        if branch_id:
            active_branch = LegalBranch.objects.filter(pk=branch_id).first()

    context = {
        'query': query,
        'record_type': record_type,
        'branch_id': branch_id,
        'tag_filter': tag_filter,
        'date_from': date_from,
        'date_to': date_to,
        'results': results,
        'total': len(results),
        'branch_facets': branch_facets,
        'tag_facets': tag_facets,
        'active_branch': active_branch,
        'all_branches': LegalBranch.objects.all(),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'search/results_partial.html', context)

    return render(request, 'search/search.html', context)
