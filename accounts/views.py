import datetime

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .forms import LoginForm, ProjectForm, RegisterForm
from .models import OAuthAccount, Project, YouTubeChannel

YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
]


def _build_flow(request):
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=YOUTUBE_SCOPES,
    )
    flow.redirect_uri = request.build_absolute_uri('/accounts/youtube/callback/')
    return flow


class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:dashboard')
        return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class DashboardView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        youtube_channel = getattr(request.user, 'youtube_channel', None)
        return render(request, 'accounts/dashboard.html', {'youtube_channel': youtube_channel})


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class YouTubeConnectView(View):
    def get(self, request):
        flow = _build_flow(request)
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
        )
        request.session['oauth_state'] = state
        return redirect(authorization_url)


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class YouTubeCallbackView(View):
    def get(self, request):
        state = request.session.get('oauth_state')
        flow = _build_flow(request)
        flow.fetch_token(
            authorization_response=request.build_absolute_uri(request.get_full_path()),
            state=state,
        )
        credentials = flow.credentials

        youtube = build('youtube', 'v3', credentials=credentials)
        channel_response = youtube.channels().list(part='snippet', mine=True).execute()
        items = channel_response.get('items', [])
        if not items:
            return render(request, 'accounts/youtube_connect_error.html', {'error': 'YouTubeチャンネルが見つかりませんでした。'})

        channel = items[0]
        channel_id = channel['id']
        channel_name = channel['snippet']['title']

        expiry = credentials.expiry
        if expiry and timezone.is_naive(expiry):
            expiry = timezone.make_aware(expiry, datetime.timezone.utc)

        oauth_account, _ = OAuthAccount.objects.update_or_create(
            user=request.user,
            provider=OAuthAccount.PROVIDER_YOUTUBE,
            defaults={
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token or '',
                'token_expiry': expiry,
            },
        )

        YouTubeChannel.objects.update_or_create(
            user=request.user,
            defaults={
                'oauth_account': oauth_account,
                'channel_id': channel_id,
                'channel_name': channel_name,
            },
        )

        return redirect('accounts:dashboard')


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class ProjectListView(View):
    def get(self, request):
        projects = Project.objects.filter(user=request.user)
        return render(request, 'accounts/project_list.html', {'projects': projects})


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class ProjectCreateView(View):
    def get(self, request):
        form = ProjectForm()
        return render(request, 'accounts/project_form.html', {'form': form})

    def post(self, request):
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            return redirect('accounts:project_list')
        return render(request, 'accounts/project_form.html', {'form': form})


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class ProjectUpdateView(View):
    def get_object(self, request, pk):
        return Project.objects.filter(pk=pk, user=request.user).first()

    def get(self, request, pk):
        project = self.get_object(request, pk)
        if not project:
            return redirect('accounts:project_list')
        form = ProjectForm(instance=project)
        return render(request, 'accounts/project_form.html', {'form': form, 'project': project})

    def post(self, request, pk):
        project = self.get_object(request, pk)
        if not project:
            return redirect('accounts:project_list')
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('accounts:project_list')
        return render(request, 'accounts/project_form.html', {'form': form, 'project': project})


@method_decorator(login_required(login_url='/accounts/login/'), name='dispatch')
class ProjectDeleteView(View):
    def post(self, request, pk):
        project = Project.objects.filter(pk=pk, user=request.user).first()
        if project:
            project.delete()
        return redirect('accounts:project_list')
