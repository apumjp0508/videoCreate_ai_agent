from django import forms

from accounts.models import User
from video_ai.models import VideoAiModel, VideoAiProvider


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
