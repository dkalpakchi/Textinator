# -*- coding: utf-8 -*-
import os
import glob
import shlex
import subprocess

from django.core.management.base import BaseCommand
from django.utils import autoreload

from Textinator.celery import app


def restart_celery():
    cmd = 'pkill celery'
    pid_file_name = "{}/run/celery/Textinator/{{}}.pid".format(os.environ['HOME'])
    log_file_name = "{}/log/celery/Textinator/%n%I.log".format(os.environ['HOME'])
    pid_files = glob.glob(pid_file_name.format("*"))
    if len(pid_files) > 0:
        for pid_file in pid_files:
            os.remove(pid_file)
    subprocess.call(shlex.split(cmd))
    cmd = 'celery -A Textinator multi start worker --pidfile={} --logfile={}'.format(
        pid_file_name.format("%n"), log_file_name
    )
    subprocess.call(shlex.split(cmd))
    app.autodiscover_tasks()


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Starting celery worker with autoreload...')
        autoreload.run_with_reloader(restart_celery)
