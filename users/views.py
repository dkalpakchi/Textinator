from django.shortcuts import render
from django.conf import settings

# Create your views here.
def user_settings(request):
    print(request.user)
    return render(request, 'users/settings.html', {
        'languages': settings.LANGUAGES
    })
