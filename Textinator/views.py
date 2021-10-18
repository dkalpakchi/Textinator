from projects.models import Project
from django.shortcuts import redirect, render


def index(request):
    if request.user.is_authenticated:
        return redirect('projects:index')
    else:
        projects = Project.objects.filter(is_open=True).all()
        return render(request, 'main.html', {
            'open_projects': [projects[i:i+3] for i in range(0, len(projects), 3)],
            'carousel': [
                ('Question Answering', '/textinator/static/images/tt_qa_ex.png'),
                ('Named Entity Recognition', '/textinator/static/images/tt_ner_ex.png'),
                ('Coreference resolution', '/textinator/static/images/tt_corefres_ex.png')
            ]
        })
