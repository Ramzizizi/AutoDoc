from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse

from .models import Norm, CourtCase, LegalOpinion


# ─── helpers ────────────────────────────────────────────────────────────────

def _label(text, length=55):
    return text[:length] + '…' if len(text) > length else text


def _norm_node(obj, is_center=False):
    return {
        'id': f'norm-{obj.pk}',
        'label': _label(obj.article or obj.title, 45),
        'title': obj.title,
        'group': 'center' if is_center else 'norm',
        'url': reverse('knowledge:norm_detail', args=[obj.pk]),
    }


def _case_node(obj, is_center=False):
    return {
        'id': f'case-{obj.pk}',
        'label': _label(obj.case_number, 45),
        'title': obj.thesis,
        'group': 'center' if is_center else 'case',
        'url': reverse('knowledge:case_detail', args=[obj.pk]),
    }


def _opinion_node(obj, is_center=False):
    return {
        'id': f'opinion-{obj.pk}',
        'label': _label(obj.title, 45),
        'title': obj.title,
        'group': 'center' if is_center else 'opinion',
        'url': reverse('knowledge:opinion_detail', args=[obj.pk]),
    }


# ─── graph API ──────────────────────────────────────────────────────────────

@login_required
def graph_data(request, record_type, pk):
    nodes, edges = [], []

    if record_type == 'norm':
        obj = get_object_or_404(Norm, pk=pk)
        center = _norm_node(obj, is_center=True)
        nodes.append(center)

        for case in obj.court_cases.select_related('branch')[:15]:
            n = _case_node(case)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

        for opinion in obj.opinions.all()[:10]:
            n = _opinion_node(opinion)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

    elif record_type == 'case':
        obj = get_object_or_404(CourtCase, pk=pk)
        center = _case_node(obj, is_center=True)
        nodes.append(center)

        for norm in obj.related_norms.all()[:15]:
            n = _norm_node(norm)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

        for opinion in obj.opinions.all()[:10]:
            n = _opinion_node(opinion)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

    elif record_type == 'opinion':
        obj = get_object_or_404(LegalOpinion, pk=pk)
        center = _opinion_node(obj, is_center=True)
        nodes.append(center)

        for norm in obj.related_norms.all()[:15]:
            n = _norm_node(norm)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

        for case in obj.related_cases.all()[:15]:
            n = _case_node(case)
            nodes.append(n)
            edges.append({'from': center['id'], 'to': n['id']})

    return JsonResponse({'nodes': nodes, 'edges': edges})


# ─── list views ─────────────────────────────────────────────────────────────

@login_required
def norm_list(request):
    qs = Norm.objects.select_related('branch').order_by('-created_at')
    branch_id = request.GET.get('branch')
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'knowledge/norm_list.html', {'page': page, 'branch_id': branch_id})


@login_required
def case_list(request):
    qs = CourtCase.objects.select_related('branch').order_by('-decision_date')
    branch_id = request.GET.get('branch')
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'knowledge/case_list.html', {'page': page, 'branch_id': branch_id})


@login_required
def opinion_list(request):
    qs = LegalOpinion.objects.select_related('author').order_by('-created_at')
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'knowledge/opinion_list.html', {'page': page})


# ─── detail views ───────────────────────────────────────────────────────────

@login_required
def norm_detail(request, pk):
    norm = get_object_or_404(Norm.objects.select_related('branch'), pk=pk)
    return render(request, 'knowledge/norm_detail.html', {'norm': norm})


@login_required
def case_detail(request, pk):
    case = get_object_or_404(CourtCase.objects.select_related('branch'), pk=pk)
    return render(request, 'knowledge/case_detail.html', {'case': case})


@login_required
def opinion_detail(request, pk):
    opinion = get_object_or_404(
        LegalOpinion.objects.select_related('author'), pk=pk
    )
    return render(request, 'knowledge/opinion_detail.html', {'opinion': opinion})
