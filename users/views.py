from django.conf import settings
from django.shortcuts import render
from django.utils import translation
from django.views.i18n import set_language, LANGUAGE_QUERY_PARAMETER


# Create your views here.
def user_settings(request):
    user = request.user
    if request.method == 'GET':
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
            'languages': [get_language_info(l) for l in available_languages],
            'fluent_in': user.profile.fluent_languages
        })
    elif request.method == "POST":
        response = set_language(request)

        lang_code = request.POST.get(LANGUAGE_QUERY_PARAMETER)
        if lang_code and translation.check_for_language(lang_code):
            user.profile.preferred_language = lang_code

        fluent_in = request.POST.getlist('fluent_in')
        if fluent_in:
            if lang_code and lang_code not in fluent_in:
                fluent_in.append(lang_code)
            user.profile.fluent_in = ",".join(fluent_in)
        user.profile.save()

        return response

