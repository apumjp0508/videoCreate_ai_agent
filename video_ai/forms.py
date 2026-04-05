from django import forms

from .models import UserVideoAiConfig, UserVideoAiCredential


class CredentialForm(forms.ModelForm):
    api_key = forms.CharField(
        label='APIキー',
        widget=forms.PasswordInput(attrs={'placeholder': 'APIキーを入力してください', 'autocomplete': 'off'}),
    )

    class Meta:
        model = UserVideoAiCredential
        fields = ['api_key']


class ConfigForm(forms.ModelForm):
    class Meta:
        model = UserVideoAiConfig
        fields = ['config_name', 'model_name', 'description', 'is_default', 'is_active']
        labels = {
            'config_name': '設定名',
            'model_name': 'モデル名',
            'description': '説明',
            'is_default': 'デフォルト設定にする',
            'is_active': '有効',
        }
        widgets = {
            'config_name': forms.TextInput(attrs={'placeholder': '例: Runway本番'}),
            'model_name': forms.TextInput(attrs={'placeholder': '例: gen-4'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
