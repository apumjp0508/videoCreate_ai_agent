from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import ConfigForm, CredentialForm
from .models import UserVideoAiConfig, UserVideoAiCredential, VideoAiProvider


class ProviderListView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request):
        providers = VideoAiProvider.objects.filter(is_active=True)
        credentials = UserVideoAiCredential.objects.filter(
            user=request.user,
        ).select_related('provider')
        credential_map = {c.provider_id: c for c in credentials}

        provider_data = []
        for provider in providers:
            credential = credential_map.get(provider.id)
            provider_data.append({
                'provider': provider,
                'credential': credential,
            })

        return render(request, 'video_ai/provider_list.html', {
            'provider_data': provider_data,
        })


class CredentialRegisterView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        existing = UserVideoAiCredential.objects.filter(
            user=request.user, provider=provider
        ).first()
        if existing:
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        form = CredentialForm()
        return render(request, 'video_ai/credential_register.html', {
            'provider': provider,
            'form': form,
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        existing = UserVideoAiCredential.objects.filter(
            user=request.user, provider=provider
        ).first()
        if existing:
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        form = CredentialForm(request.POST)
        if form.is_valid():
            credential = form.save(commit=False)
            credential.user = request.user
            credential.provider = provider
            credential.save()
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        return render(request, 'video_ai/credential_register.html', {
            'provider': provider,
            'form': form,
        })


class CredentialDetailView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        credential = get_object_or_404(
            UserVideoAiCredential, user=request.user, provider=provider
        )
        configs = UserVideoAiConfig.objects.filter(
            user=request.user, provider=provider
        ).order_by('-is_default', '-created_at')

        return render(request, 'video_ai/credential_detail.html', {
            'provider': provider,
            'credential': credential,
            'configs': configs,
        })


class CredentialUpdateView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        credential = get_object_or_404(
            UserVideoAiCredential, user=request.user, provider=provider
        )
        form = CredentialForm(instance=credential)
        return render(request, 'video_ai/credential_update.html', {
            'provider': provider,
            'credential': credential,
            'form': form,
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        credential = get_object_or_404(
            UserVideoAiCredential, user=request.user, provider=provider
        )
        form = CredentialForm(request.POST, instance=credential)
        if form.is_valid():
            credential = form.save(commit=False)
            credential.test_status = UserVideoAiCredential.TEST_STATUS_UNTESTED
            credential.save()
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        return render(request, 'video_ai/credential_update.html', {
            'provider': provider,
            'credential': credential,
            'form': form,
        })


class ConfigCreateView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        credential = get_object_or_404(
            UserVideoAiCredential, user=request.user, provider=provider
        )
        form = ConfigForm()
        return render(request, 'video_ai/config_form.html', {
            'provider': provider,
            'credential': credential,
            'form': form,
            'action': 'create',
        })

    def post(self, request, provider_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        credential = get_object_or_404(
            UserVideoAiCredential, user=request.user, provider=provider
        )
        form = ConfigForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                config = form.save(commit=False)
                config.user = request.user
                config.provider = provider
                config.credential = credential
                if config.is_default:
                    UserVideoAiConfig.objects.filter(
                        user=request.user, provider=provider
                    ).update(is_default=False)
                config.save()
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        return render(request, 'video_ai/config_form.html', {
            'provider': provider,
            'credential': credential,
            'form': form,
            'action': 'create',
        })


class ConfigUpdateView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, provider_id, config_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        config = get_object_or_404(
            UserVideoAiConfig, id=config_id, user=request.user, provider=provider
        )
        form = ConfigForm(instance=config)
        return render(request, 'video_ai/config_form.html', {
            'provider': provider,
            'credential': config.credential,
            'form': form,
            'action': 'update',
            'config': config,
        })

    def post(self, request, provider_id, config_id):
        provider = get_object_or_404(VideoAiProvider, id=provider_id, is_active=True)
        config = get_object_or_404(
            UserVideoAiConfig, id=config_id, user=request.user, provider=provider
        )
        form = ConfigForm(request.POST, instance=config)
        if form.is_valid():
            with transaction.atomic():
                updated = form.save(commit=False)
                if updated.is_default:
                    UserVideoAiConfig.objects.filter(
                        user=request.user, provider=provider
                    ).exclude(id=config_id).update(is_default=False)
                updated.save()
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        return render(request, 'video_ai/config_form.html', {
            'provider': provider,
            'credential': config.credential,
            'form': form,
            'action': 'update',
            'config': config,
        })
