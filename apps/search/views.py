from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Value, FloatField
from django.db import connection
from django.urls import reverse

from apps.knowledge.models import Norm, CourtCase, LegalOpinion


def _fts_results(query, record_type):
    from django.contrib.postgres.search import (
        SearchVector, SearchQuery, SearchRank, SearchHeadline,
    )

    search_query = SearchQuery(query, config='russian', search_type='websearch')
    headline_opts = dict(config='russian', max_words=40, min_words=20, highlight_all=False)

    results = []

    if not record_type or record_type == 'norm':
        vec = SearchVector('title', 'article', 'text', config='russian')
        qs = (
            Norm.objects
            .annotate(search=vec, rank=SearchRank(vec, search_query),
                      snippet=SearchHeadline('text', search_query, **headline_opts))
            .filter(search=search_query)
            .select_related('branch')
            .order_by('-rank')[:20]
        )
        for obj in qs:
            results.append({
                'type': 'norm',
                'type_label': 'Норма права',
                'type_color': 'primary',
                'title': obj.title,
                'subtitle': obj.get_norm_type_display(),
                'snippet': obj.snippet,
                'rank': float(obj.rank),
                'url': reverse('knowledge:norm_detail', args=[obj.pk]),
                'branch': str(obj.branch) if obj.branch else '',
                'tags': list(obj.tags.names()),
            })

    if not record_type or record_type == 'case':
        vec = SearchVector('case_number', 'thesis', 'text', config='russian')
        qs = (
            CourtCase.objects
            .annotate(search=vec, rank=SearchRank(vec, search_query),
                      snippet=SearchHeadline('thesis', search_query, **headline_opts))
            .filter(search=search_query)
            .select_related('branch')
            .order_by('-rank')[:20]
        )
        for obj in qs:
            results.append({
                'type': 'case',
                'type_label': 'Судебная практика',
                'type_color': 'success',
                'title': obj.thesis,
                'subtitle': obj.court,
                'snippet': obj.snippet,
                'rank': float(obj.rank),
                'url': reverse('knowledge:case_detail', args=[obj.pk]),
                'branch': str(obj.branch) if obj.branch else '',
                'tags': list(obj.tags.names()),
            })

    if not record_type or record_type == 'opinion':
        vec = SearchVector('title', 'text', config='russian')
        qs = (
            LegalOpinion.objects
            .annotate(search=vec, rank=SearchRank(vec, search_query),
                      snippet=SearchHeadline('text', search_query, **headline_opts))
            .filter(search=search_query)
            .order_by('-rank')[:20]
        )
        for obj in qs:
            results.append({
                'type': 'opinion',
                'type_label': 'Правовое заключение',
                'type_color': 'warning',
                'title': obj.title,
                'subtitle': f'Автор: {obj.author}' if obj.author else '',
                'snippet': obj.snippet,
                'rank': float(obj.rank),
                'url': reverse('knowledge:opinion_detail', args=[obj.pk]),
                'branch': '',
                'tags': list(obj.tags.names()),
            })

    results.sort(key=lambda x: x['rank'], reverse=True)
    return results


def _fallback_results(query, record_type):
    """icontains fallback for SQLite (local dev without PostgreSQL)."""
    results = []

    if not record_type or record_type == 'norm':
        qs = Norm.objects.filter(
            Q(title__icontains=query) | Q(text__icontains=query) | Q(article__icontains=query)
        ).select_related('branch')[:20]
        for obj in qs:
            results.append({
                'type': 'norm', 'type_label': 'Норма права', 'type_color': 'primary',
                'title': obj.title, 'subtitle': obj.get_norm_type_display(),
                'snippet': obj.text[:200] + '…' if len(obj.text) > 200 else obj.text,
                'rank': 1.0,
                'url': reverse('knowledge:norm_detail', args=[obj.pk]),
                'branch': str(obj.branch) if obj.branch else '',
                'tags': list(obj.tags.names()),
            })

    if not record_type or record_type == 'case':
        qs = CourtCase.objects.filter(
            Q(thesis__icontains=query) | Q(text__icontains=query) | Q(case_number__icontains=query)
        ).select_related('branch')[:20]
        for obj in qs:
            results.append({
                'type': 'case', 'type_label': 'Судебная практика', 'type_color': 'success',
                'title': obj.thesis, 'subtitle': obj.court,
                'snippet': obj.text[:200] + '…' if len(obj.text) > 200 else obj.text,
                'rank': 1.0,
                'url': reverse('knowledge:case_detail', args=[obj.pk]),
                'branch': str(obj.branch) if obj.branch else '',
                'tags': list(obj.tags.names()),
            })

    if not record_type or record_type == 'opinion':
        qs = LegalOpinion.objects.filter(
            Q(title__icontains=query) | Q(text__icontains=query)
        )[:20]
        for obj in qs:
            results.append({
                'type': 'opinion', 'type_label': 'Правовое заключение', 'type_color': 'warning',
                'title': obj.title, 'subtitle': f'Автор: {obj.author}' if obj.author else '',
                'snippet': obj.text[:200] + '…' if len(obj.text) > 200 else obj.text,
                'rank': 1.0,
                'url': reverse('knowledge:opinion_detail', args=[obj.pk]),
                'branch': '',
                'tags': list(obj.tags.names()),
            })

    return results


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    record_type = request.GET.get('type', '').strip()

    results = []
    if query:
        if connection.vendor == 'postgresql':
            results = _fts_results(query, record_type)
        else:
            results = _fallback_results(query, record_type)

    context = {
        'query': query,
        'record_type': record_type,
        'results': results,
        'total': len(results),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'search/results_partial.html', context)

    return render(request, 'search/search.html', context)
