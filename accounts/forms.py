from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    class Meta:
        model = User
        fields = ['email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise forms.ValidationError('Passwords do not match')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    pass


class ContentSelectForm(forms.Form):
    """
    script / image / audio を選択するフォーム（動画作成ステップ2）。

    image と audio の choices はビューから動的にセットする。
    channel_id に応じて候補が変わる設計になっている。

    TODO: DB完成後は、ビュー側の dummy_data.py の関数をDB取得に差し替えるだけでOK。
          このフォームクラス自体は変更不要。
    """

    # script: 将来的には「定型文から選択」や「AI自動生成」に変える可能性あり。
    # 今は自由入力テキストエリアで実装。
    script = forms.CharField(
        label='スクリプト',
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': '動画のスクリプトを入力してください',
        }),
    )

    # image / audio は choices を空で定義し、__init__ でビューからセットする
    image = forms.ChoiceField(
        label='画像',
        choices=[],  # ビューから image_choices を渡してセットする
    )

    audio = forms.ChoiceField(
        label='音声',
        choices=[],  # ビューから audio_choices を渡してセットする
    )

    def __init__(self, *args, image_choices=None, audio_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        # ビューからチャンネルに応じた選択肢を受け取ってセットする
        if image_choices is not None:
            self.fields['image'].choices = image_choices
        if audio_choices is not None:
            self.fields['audio'].choices = audio_choices


class ImageUploadForm(forms.Form):
    """
    画像アップロード用フォーム。

    今回はUI・遷移の骨組みのみ。実際のファイル保存は行わない。
    TODO: DB完成後に画像メタ情報（タイトルなど）をDBに保存する
    TODO: 実ファイルの保存処理（ストレージへの書き込み）は今後追加する
    TODO: channel や user との紐づけは今後追加する
    """
    title = forms.CharField(
        label='画像タイトル',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': '例: 背景画像_都市風景'}),
    )
    # enctype="multipart/form-data" が必要（テンプレート側で設定済み）
    file = forms.ImageField(
        label='画像ファイル',
        # TODO: 将来は validators でファイルサイズ上限などを追加する
    )


class AudioUploadForm(forms.Form):
    """
    音声アップロード用フォーム。

    今回はUI・遷移の骨組みのみ。実際のファイル保存は行わない。
    TODO: DB完成後に音声メタ情報（タイトルなど）をDBに保存する
    TODO: 実ファイルの保存処理（ストレージへの書き込み）は今後追加する
    TODO: channel や user との紐づけは今後追加する
    """
    title = forms.CharField(
        label='音声タイトル',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': '例: BGM_明るい曲'}),
    )
    file = forms.FileField(
        label='音声ファイル',
        # TODO: 将来は validators で mp3/wav などの形式チェックを追加する
    )
