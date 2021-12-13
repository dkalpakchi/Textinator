import time
import random
from django.db import migrations


def short2code(apps, schema_editor):
    Marker = apps.get_model('projects', 'Marker')

    for m in Marker.objects.all().iterator():
        m.code = "{}_{}_{}".format(m.short, str(int(time.time())), random.randint(0, 9999))
        m.save()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0113_auto_20211213_1017'),
    ]

    operations = [
        migrations.RunPython(short2code, migrations.RunPython.noop),
    ]
