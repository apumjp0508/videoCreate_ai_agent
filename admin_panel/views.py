from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import User
from video_ai.models import VideoAiModel, VideoAiProvider, VideoAiProviderValidationConfig

from .forms import AdminLoginForm, ProviderForm, UserCreateForm, UserEditForm, ValidationConfigForm, VideoAiModelForm
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
        validation_count = VideoAiProviderValidationConfig.objects.count()
        return render(request, 'admin_panel/dashboard.html', {
            'user_count': user_count,
            'provider_count': provider_count,
            'validation_count': validation_count,
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


# ---------- AIモデル管理 ----------

class ModelListView(StaffRequiredMixin, View):
    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        models_qs = VideoAiModel.objects.filter(provider=provider).order_by('model_name')
        return render(request, 'admin_panel/model_list.html', {
            'provider': provider,
            'models': models_qs,
        })


class ModelCreateView(StaffRequiredMixin, View):
    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        form = VideoAiModelForm()
        return render(request, 'admin_panel/model_form.html', {
            'provider': provider,
            'form': form,
            'action': 'create',
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        form = VideoAiModelForm(request.POST)
        if form.is_valid():
            model = form.save(commit=False)
            model.provider = provider
            model.save()
            messages.success(request, f'モデル「{model.model_name}」を追加しました。')
            return redirect('admin_panel:model_list', provider_id=provider_id)
        return render(request, 'admin_panel/model_form.html', {
            'provider': provider,
            'form': form,
            'action': 'create',
        })


class ModelEditView(StaffRequiredMixin, View):
    def get(self, request, provider_id, model_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        model = get_object_or_404(VideoAiModel, id=model_id, provider=provider)
        form = VideoAiModelForm(instance=model)
        return render(request, 'admin_panel/model_form.html', {
            'provider': provider,
            'form': form,
            'action': 'edit',
            'model': model,
        })

    def post(self, request, provider_id, model_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        model = get_object_or_404(VideoAiModel, id=model_id, provider=provider)
        form = VideoAiModelForm(request.POST, instance=model)
        if form.is_valid():
            form.save()
            messages.success(request, f'モデル「{model.model_name}」を更新しました。')
            return redirect('admin_panel:model_list', provider_id=provider_id)
        return render(request, 'admin_panel/model_form.html', {
            'provider': provider,
            'form': form,
            'action': 'edit',
            'model': model,
        })


class ModelDeleteView(StaffRequiredMixin, View):
    def post(self, request, provider_id, model_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        model = get_object_or_404(VideoAiModel, id=model_id, provider=provider)
        name = model.model_name
        model.delete()
        messages.success(request, f'モデル「{name}」を削除しました。')
        return redirect('admin_panel:model_list', provider_id=provider_id)


class ModelToggleView(StaffRequiredMixin, View):
    def post(self, request, provider_id, model_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        model = get_object_or_404(VideoAiModel, id=model_id, provider=provider)
        model.is_active = not model.is_active
        model.save(update_fields=['is_active'])
        status = '有効' if model.is_active else '無効'
        messages.success(request, f'「{model.model_name}」を{status}にしました。')
        return redirect('admin_panel:model_list', provider_id=provider_id)


# ---------- バリデーション設定管理 ----------

class ValidationConfigListView(StaffRequiredMixin, View):
    """全プロバイダーのバリデーション設定一覧を表示する。"""

    def get(self, request):
        providers = VideoAiProvider.objects.order_by('id').select_related('validation_config')
        return render(request, 'admin_panel/validation_list.html', {'providers': providers})


class ValidationConfigView(StaffRequiredMixin, View):
    """プロバイダーのバリデーション設定を表示・編集する（存在しなければ作成フォームへ）。"""

    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        try:
            config = provider.validation_config
        except VideoAiProviderValidationConfig.DoesNotExist:
            return redirect('admin_panel:validation_config_create', provider_id=provider_id)
        form = ValidationConfigForm(instance=config)
        return render(request, 'admin_panel/validation_config_form.html', {
            'provider': provider,
            'form': form,
            'action': 'edit',
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        config = get_object_or_404(VideoAiProviderValidationConfig, provider=provider)
        form = ValidationConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f'{provider.provider_name} のバリデーション設定を更新しました。')
            return redirect('admin_panel:validation_list')
        return render(request, 'admin_panel/validation_config_form.html', {
            'provider': provider,
            'form': form,
            'action': 'edit',
        })


class ValidationConfigCreateView(StaffRequiredMixin, View):
    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        if hasattr(provider, 'validation_config'):
            return redirect('admin_panel:validation_config', provider_id=provider_id)
        form = ValidationConfigForm()
        return render(request, 'admin_panel/validation_config_form.html', {
            'provider': provider,
            'form': form,
            'action': 'create',
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        form = ValidationConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.provider = provider
            config.save()
            messages.success(request, f'{provider.provider_name} のバリデーション設定を作成しました。')
            return redirect('admin_panel:validation_list')
        return render(request, 'admin_panel/validation_config_form.html', {
            'provider': provider,
            'form': form,
            'action': 'create',
        })


class ValidationConfigDeleteView(StaffRequiredMixin, View):
    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id)
        config = get_object_or_404(VideoAiProviderValidationConfig, provider=provider)
        config.delete()
        messages.success(request, f'{provider.provider_name} のバリデーション設定を削除しました。')
        return redirect('admin_panel:validation_list')
