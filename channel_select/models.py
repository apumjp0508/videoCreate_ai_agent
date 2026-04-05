from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'

    def __str__(self):
        return self.name


class ProjectChannel(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='channels')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_channels'

    def __str__(self):
        return self.name


class GeneratedImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    project_channel = models.ForeignKey(
        ProjectChannel, on_delete=models.SET_NULL, null=True, blank=True, related_name='images'
    )
    image_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255, null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_path = models.TextField(null=True, blank=True)
    file_url = models.TextField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_images'

    def __str__(self):
        return self.title or str(self.id)


class GeneratedAudio(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='audios')
    project_channel = models.ForeignKey(
        ProjectChannel, on_delete=models.SET_NULL, null=True, blank=True, related_name='audios'
    )
    audio_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255, null=True, blank=True)
    script_text = models.TextField(null=True, blank=True)
    voice_name = models.CharField(max_length=100, null=True, blank=True)
    language_code = models.CharField(max_length=20, null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_path = models.TextField(null=True, blank=True)
    file_url = models.TextField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_audios'

    def __str__(self):
        return self.title or str(self.id)
