from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views import View

from .forms import LoginForm, RegisterForm


class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:dashboard')
        return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class DashboardView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return render(request, 'accounts/dashboard.html')
