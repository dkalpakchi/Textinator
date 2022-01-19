import os
import json

from django.shortcuts import redirect, render
from django.conf import settings

from projects.models import Project
from Textinator import VERSION


def index(request):
    if request.user.is_authenticated:
        return redirect('projects:index')
    else:
        projects = Project.objects.filter(is_open=True).all()
        return render(request, 'main.html', {
            'open_projects': [projects[i:i+3] for i in range(0, len(projects), 3)],
            'carousel': [
                ('Question Answering', '/{}static/images/tt_qa_ex.png'.format(settings.ROOT_URLPATH)),
                ('Named Entity Recognition', '/{}static/images/tt_ner_ex.png'.format(settings.ROOT_URLPATH)),
                ('Coreference resolution', '/{}static/images/tt_corefres_ex.png'.format(settings.ROOT_URLPATH))
            ],
            'version': "v{}".format(VERSION),
            "oss_tools": json.load(open(os.path.join(os.path.dirname(__file__), 'tools_comparison.json')))["tools"]
        })
