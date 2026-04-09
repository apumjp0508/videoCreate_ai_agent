import logging
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .api_key_validator import ApiKeyValidationResult, validate_api_key
from .forms import CredentialForm
from .models import UserVideoAiCredential, VideoAiProvider

logger = logging.getLogger(__name__)

_APP_ENV_LOCAL = "local"


def _is_local_env() -> bool:
    return os.environ.get("APP_ENV", _APP_ENV_LOCAL).strip().lower() == _APP_ENV_LOCAL


def _dummy_validation_result(credential: UserVideoAiCredential) -> ApiKeyValidationResult:
    """local環境用: 実際のリクエストを行わず成功扱いのダミー結果を返す。"""
    dummy_url = (
        credential.provider.api_base_url.rstrip("/") + "/dummy/validation"
    )
    return ApiKeyValidationResult(
        http_status=200,
        validation_endpoint=dummy_url,
        error_code=None,
        is_valid=True,
    )


def _run_api_key_validation(credential: UserVideoAiCredential) -> None:
    """
    credentialのAPIキーを検証してDB上の検証フィールドを更新する。

    APP_ENV=local  → ダミー結果（常に成功）を使用
    APP_ENV=staging → 実際のAPIエンドポイントへリクエストを送信

    検証失敗（接続エラー含む）でも例外を外部に伝播させない。
    """
    try:
        if _is_local_env():
            result = _dummy_validation_result(credential)
            logger.info(
                "[local] API key validation skipped  provider=%s",
                credential.provider.provider_key,
            )
        else:
            result = validate_api_key(
                api_key=credential.api_key,
                provider_key=credential.provider.provider_key,
                base_url=credential.provider.api_base_url,
            )

        credential.validation_http_status = result.http_status
        credential.validation_endpoint    = result.validation_endpoint
        credential.validation_error_code  = result.error_code
        credential.test_status = (
            UserVideoAiCredential.TEST_STATUS_SUCCESS
            if result.is_valid
            else UserVideoAiCredential.TEST_STATUS_FAILED
        )
        credential.is_active = result.is_valid
        credential.save(update_fields=[
            'validation_http_status',
            'validation_endpoint',
            'validation_error_code',
            'test_status',
            'is_active',
        ])
    except KeyError:
        # 未登録プロバイダー: 検証をスキップ（test_status は untested のまま）
        logger.info(
            "No validator registered for provider '%s', skipping API key validation.",
            credential.provider.provider_key,
        )
    except Exception:
        logger.exception(
            "Unexpected error during API key validation for provider '%s'.",
            credential.provider.provider_key,
        )


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
            _run_api_key_validation(credential)
            if credential.test_status == UserVideoAiCredential.TEST_STATUS_SUCCESS:
                messages.success(request, 'APIキーを登録し、検証に成功しました。')
            elif credential.test_status == UserVideoAiCredential.TEST_STATUS_FAILED:
                messages.warning(request, 'APIキーを登録しましたが、検証に失敗しました。キーを確認してください。')
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
        return render(request, 'video_ai/credential_detail.html', {
            'provider': provider,
            'credential': credential,
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
            # 検証フィールドをリセットしてから再検証
            credential.validation_http_status = None
            credential.validation_endpoint    = None
            credential.validation_error_code  = None
            credential.save()
            _run_api_key_validation(credential)
            if credential.test_status == UserVideoAiCredential.TEST_STATUS_SUCCESS:
                messages.success(request, 'APIキーを更新し、検証に成功しました。')
            elif credential.test_status == UserVideoAiCredential.TEST_STATUS_FAILED:
                messages.warning(request, 'APIキーを更新しましたが、検証に失敗しました。キーを確認してください。')
            return redirect('video_ai:credential_detail', provider_id=provider_id)

        return render(request, 'video_ai/credential_update.html', {
            'provider': provider,
            'credential': credential,
            'form': form,
        })


