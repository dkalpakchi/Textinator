from django.conf import settings
from django.shortcuts import render
from django.utils import translation


# Create your views here.
def user_settings(request):
    def get_language_info(language):
        # ``language`` is either a language code string or a sequence
        # with the language code as its first item
        if len(language[0]) > 1:
            return translation.get_language_info(language[0])
        else:
            return translation.get_language_info(str(language))

    available_languages = [
        (k, translation.gettext(v)) for k, v in settings.LANGUAGES
    ]
    return render(request, 'users/settings.html', {
        'current_language': translation.get_language(),
        'available_languages': available_languages,
        'languages': [get_language_info(l) for l in available_languages]
    })
