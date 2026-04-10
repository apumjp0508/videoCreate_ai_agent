import json

from django import forms

from accounts.models import User
from video_ai.models import VideoAiModel, VideoAiProvider, VideoAiProviderValidationConfig


class AdminLoginForm(forms.Form):
    email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={'placeholder': 'admin@example.com', 'autofocus': True}),
    )
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={'placeholder': 'パスワード'}),
    )


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'is_active', 'is_staff', 'is_superuser']
        labels = {
            'email': 'メールアドレス',
            'is_active': 'アクティブ',
            'is_staff': 'スタッフ（管理画面アクセス可）',
            'is_superuser': 'スーパーユーザー',
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        labels = {
            'email': 'メールアドレス',
            'is_active': 'アクティブ',
            'is_staff': 'スタッフ（管理画面アクセス可）',
            'is_superuser': 'スーパーユーザー',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class VideoAiModelForm(forms.ModelForm):
    class Meta:
        model = VideoAiModel
        fields = ['model_name', 'is_active']
        labels = {
            'model_name': 'モデル名',
            'is_active': '有効',
        }
        widgets = {
            'model_name': forms.TextInput(attrs={'placeholder': '例: gen-4'}),
        }


class JsonListField(forms.CharField):
    """カンマ区切りテキスト → JSON リスト に変換するフィールド。"""

    def __init__(self, *args, required=True, **kwargs):
        kwargs.setdefault('widget', forms.Textarea(attrs={'rows': 2, 'placeholder': 'image/jpeg, image/png, image/webp'}))
        super().__init__(*args, required=required, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        if value is None:
            return ''
        return value

    def to_python(self, value):
        value = super().to_python(value).strip()
        if not value:
            return None
        return [item.strip() for item in value.split(',') if item.strip()]


class JsonIntListField(forms.CharField):
    """カンマ区切りテキスト → 整数 JSON リスト。"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput(attrs={'placeholder': '例: 1, 2'}))
        super().__init__(*args, required=False, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        if value is None:
            return ''
        return value

    def to_python(self, value):
        value = super().to_python(value).strip()
        if not value:
            return None
        try:
            return [int(item.strip()) for item in value.split(',') if item.strip()]
        except ValueError:
            raise forms.ValidationError('整数をカンマ区切りで入力してください（例: 1, 2）')


class ValidationConfigForm(forms.ModelForm):
    image_allowed_mime_types = JsonListField(
        label='許可する画像 MIME タイプ（カンマ区切り）',
    )
    image_allowed_aspect_ratios = JsonListField(
        label='許可するアスペクト比（カンマ区切り）',
        required=False,
    )
    audio_allowed_mime_types = JsonListField(
        label='許可する音声 MIME タイプ（カンマ区切り）',
        required=False,
    )
    audio_allowed_channels = JsonIntListField(
        label='許可チャンネル数（カンマ区切り）',
    )

    class Meta:
        model = VideoAiProviderValidationConfig
        exclude = ['provider']
        labels = {
            'image_max_size_bytes': '画像最大サイズ（bytes）',
            'image_max_size_soft_bytes': '画像推奨最大サイズ（bytes）',
            'image_min_dimension': '画像最小辺長（px）',
            'image_max_dimension': '画像最大辺長（px）',
            'image_min_dimension_recommended': '推奨最小辺長（px）',
            'image_max_dimension_recommended': '推奨最大辺長（px）',
            'image_aspect_ratio_required': 'アスペクト比違反をエラーにする',
            'audio_is_supported': '音声入力に対応',
            'audio_unsupported_message': '音声未対応メッセージ',
            'audio_max_size_bytes': '音声最大サイズ（bytes）',
            'audio_max_duration_sec': '音声最大長（秒）',
            'audio_min_sample_rate': '最小サンプルレート（Hz）',
            'audio_max_sample_rate': '最大サンプルレート（Hz）',
        }


class ProviderForm(forms.ModelForm):
    class Meta:
        model = VideoAiProvider
        fields = ['provider_key', 'provider_name', 'api_base_url', 'docs_url', 'is_active']
        labels = {
            'provider_key': 'プロバイダーキー（英数字）',
            'provider_name': 'サービス名',
            'api_base_url': 'API ベース URL',
            'docs_url': '公式ドキュメント URL',
            'is_active': '有効',
        }
        widgets = {
            'provider_key': forms.TextInput(attrs={'placeholder': '例: runway'}),
            'provider_name': forms.TextInput(attrs={'placeholder': '例: Runway'}),
            'api_base_url': forms.URLInput(attrs={'placeholder': 'https://api.example.com'}),
            'docs_url': forms.URLInput(attrs={'placeholder': 'https://docs.example.com'}),
        }
