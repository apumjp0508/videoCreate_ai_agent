from django.shortcuts import redirect


class StaffRequiredMixin:
    """is_staff=True のユーザーのみアクセス可能。
    未認証・非スタッフどちらも /admin-panel/login/ へリダイレクト。
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('admin_panel:login')
        return super().dispatch(request, *args, **kwargs)
