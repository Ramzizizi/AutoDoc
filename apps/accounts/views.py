from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse_lazy

from apps.knowledge.models import LegalOpinion


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


@login_required
def profile(request):
    opinions_count = LegalOpinion.objects.filter(author=request.user).count()
    return render(request, 'accounts/profile.html', {'opinions_count': opinions_count})
