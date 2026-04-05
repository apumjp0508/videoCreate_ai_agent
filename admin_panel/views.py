from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import User
from video_ai.models import VideoAiProvider

from .forms import AdminLoginForm, ProviderForm, UserCreateForm, UserEditForm
from .mixins import StaffRequiredMixin


# ---------- 管理者ログイン ----------

class AdminLoginView(View):
    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('admin_panel:dashboard')
        form = AdminLoginForm()
        return render(request, 'admin_panel/login.html', {'form': form})

    def post(self, request):
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                return redirect('admin_panel:dashboard')
            form.add_error(None, 'メールアドレスまたはパスワードが正しくないか、管理者権限がありません。')
        return render(request, 'admin_panel/login.html', {'form': form})


class AdminLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('admin_panel:login')


# ---------- ダッシュボード ----------

class AdminDashboardView(StaffRequiredMixin, View):
    def get(self, request):
        user_count = User.objects.count()
        provider_count = VideoAiProvider.objects.count()
        return render(request, 'admin_panel/dashboard.html', {
            'user_count': user_count,
            'provider_count': provider_count,
        })


# ---------- ユーザー管理 ----------

class UserListView(StaffRequiredMixin, View):
    def get(self, request):
        users = User.objects.order_by('email')
        return render(request, 'admin_panel/user_list.html', {'users': users})


class UserCreateView(StaffRequiredMixin, View):
    def get(self, request):
        form = UserCreateForm()
        return render(request, 'admin_panel/user_form.html', {'form': form, 'action': 'create'})

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザーを作成しました。')
            return redirect('admin_panel:user_list')
        return render(request, 'admin_panel/user_form.html', {'form': form, 'action': 'create'})


class UserEditView(StaffRequiredMixin, View):
    def get(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        form = UserEditForm(instance=target)
        return render(request, 'admin_panel/user_form.html', {
            'form': form,
            'action': 'edit',
            'target_user': target,
        })

    def post(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザー情報を更新しました。')
            return redirect('admin_panel:user_list')
        return render(request, 'admin_panel/user_form.html', {
            'form': form,
            'action': 'edit',
            'target_user': target,
        })


class UserDeleteView(StaffRequiredMixin, View):
    def post(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        if target == request.user:
            messages.error(request, '自分自身は削除できません。')
            return redirect('admin_panel:user_list')
        target.delete()
        messages.success(request, 'ユーザーを削除しました。')
        return redirect('admin_panel:user_list')


# ---------- AIプロバイダー管理 ----------

class ProviderListView(StaffRequiredMixin, View):
    def get(self, request):
        providers = VideoAiProvider.objects.order_by('id')
        return render(request, 'admin_panel/provider_list.html', {'providers': providers})


class ProviderToggleView(StaffRequiredMixin, View):
    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        provider.is_active = not provider.is_active
        provider.save(update_fields=['is_active'])
        status = '有効' if provider.is_active else '無効'
        messages.success(request, f'{provider.provider_name} を{status}にしました。')
        return redirect('admin_panel:provider_list')


class ProviderCreateView(StaffRequiredMixin, View):
    def get(self, request):
        form = ProviderForm()
        return render(request, 'admin_panel/provider_form.html', {'form': form, 'action': 'create'})

    def post(self, request):
        form = ProviderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'プロバイダーを追加しました。')
            return redirect('admin_panel:provider_list')
        return render(request, 'admin_panel/provider_form.html', {'form': form, 'action': 'create'})


class ProviderEditView(StaffRequiredMixin, View):
    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        form = ProviderForm(instance=provider)
        return render(request, 'admin_panel/provider_form.html', {
            'form': form,
            'action': 'edit',
            'provider': provider,
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        form = ProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, 'プロバイダー情報を更新しました。')
            return redirect('admin_panel:provider_list')
        return render(request, 'admin_panel/provider_form.html', {
            'form': form,
            'action': 'edit',
            'provider': provider,
        })


class ProviderDeleteView(StaffRequiredMixin, View):
    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        provider.delete()
        messages.success(request, 'プロバイダーを削除しました。')
        return redirect('admin_panel:provider_list')
