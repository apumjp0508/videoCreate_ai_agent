from django import forms

from .models import UserVideoAiCredential


class CredentialForm(forms.ModelForm):
    api_key = forms.CharField(
        label='APIキー',
        widget=forms.PasswordInput(attrs={'placeholder': 'APIキーを入力してください', 'autocomplete': 'off'}),
    )

    class Meta:
        model = UserVideoAiCredential
        fields = ['api_key']
