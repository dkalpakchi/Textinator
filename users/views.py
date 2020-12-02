from django.shortcuts import render

# Create your views here.
def user_settings(request):
    print(request.user)
    return render(request, 'users/settings.html', {})
