from django import forms


class ContentSelectForm(forms.Form):
    """
    script / image / audio を選択するフォーム（動画作成ステップ2）。
    image と audio の choices はビューから動的にセットする。
    """
    script = forms.CharField(
        label='スクリプト',
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': '動画のスクリプトを入力してください',
        }),
    )
    image = forms.ChoiceField(
        label='画像',
        choices=[],
        required=False,
    )
    audio = forms.ChoiceField(
        label='音声',
        choices=[],
        required=False,
    )

    publish_mode = forms.ChoiceField(
        label='公開設定',
        choices=[
            ('private',  '非公開'),
            ('unlisted', '限定公開'),
            ('public',   '公開'),
        ],
        initial='private',
    )

    def __init__(self, *args, image_choices=None, audio_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if image_choices is not None:
            self.fields['image'].choices = image_choices
        if audio_choices is not None:
            self.fields['audio'].choices = audio_choices


class ImageUploadForm(forms.Form):
    """画像新規アップロード用フォーム。file は必須。"""
    title = forms.CharField(
        label='画像タイトル',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': '例: 背景画像_都市風景'}),
    )
    file = forms.FileField(label='画像ファイル')


class ImageEditForm(forms.Form):
    """画像編集用フォーム。file は変更しない場合は省略可。"""
    title = forms.CharField(
        label='画像タイトル',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': '例: 背景画像_都市風景'}),
    )
    file = forms.FileField(
        label='画像ファイル（変更する場合のみ選択）',
        required=False,
    )


class AudioUploadForm(forms.Form):
    """音声新規アップロード用フォーム。file は必須。"""
    title = forms.CharField(
        label='音声タイトル',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': '例: BGM_明るい曲'}),
    )
    file = forms.FileField(label='音声ファイル')


class AudioEditForm(forms.Form):
    """音声編集用フォーム。file は変更しない場合は省略可。"""
    title = forms.CharField(
        label='音声タイトル',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': '例: BGM_明るい曲'}),
    )
    file = forms.FileField(
        label='音声ファイル（変更する場合のみ選択）',
        required=False,
    )


# ─────────────────────── AI Provider + Model ───────────────────────

class AIProviderSelectForm(forms.Form):
    """
    動画生成に使う AI プロバイダとモデルを選択するフォーム（動画作成ステップ3）。
    choices はビューから動的にセットする（ユーザーの登録済み credential と
    管理者が有効にした VideoAiModel を元に構築する）。
    """
    provider = forms.ChoiceField(
        label='生成AI',
        choices=[],
        widget=forms.RadioSelect,
    )
    model_id = forms.ChoiceField(
        label='モデル',
        choices=[],
    )

    def __init__(self, *args, provider_choices=None, model_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if provider_choices is not None:
            self.fields['provider'].choices = provider_choices
        if model_choices is not None:
            self.fields['model_id'].choices = model_choices
