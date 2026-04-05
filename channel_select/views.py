from django.shortcuts import render, get_object_or_404
from .models import ProjectChannel, GeneratedImage, GeneratedAudio


def channel_list(request):
    channels = ProjectChannel.objects.select_related('project').order_by('project__name', 'name')
    return render(request, 'channel_select/channel_list.html', {'channels': channels})


def channel_detail(request, channel_id):
    channel = get_object_or_404(ProjectChannel, id=channel_id)

    images = GeneratedImage.objects.filter(
        project_channel_id=channel_id
    ).only('id', 'title').order_by('id')

    audios = GeneratedAudio.objects.filter(
        project_channel_id=channel_id
    ).only('id', 'title').order_by('id')

    return render(request, 'channel_select/channel_detail.html', {
        'channel': channel,
        'images': images,
        'audios': audios,
    })
