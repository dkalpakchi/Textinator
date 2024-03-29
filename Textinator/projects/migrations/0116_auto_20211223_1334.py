# -*- coding: utf-8 -*-
# Generated by Django 3.2.10 on 2021-12-23 13:34

import colorfield.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import filebrowser.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0115_auto_20211213_1019'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='batch',
            options={'verbose_name': 'annotation batch', 'verbose_name_plural': 'annotation batches'},
        ),
        migrations.AlterModelOptions(
            name='context',
            options={'verbose_name': 'context', 'verbose_name_plural': 'contexts'},
        ),
        migrations.AlterModelOptions(
            name='dataaccesslog',
            options={'verbose_name': 'data access log', 'verbose_name_plural': 'data access logs'},
        ),
        migrations.AlterModelOptions(
            name='datasource',
            options={'verbose_name': 'data source', 'verbose_name_plural': 'data sources'},
        ),
        migrations.AlterModelOptions(
            name='input',
            options={'verbose_name': 'input', 'verbose_name_plural': 'inputs'},
        ),
        migrations.AlterModelOptions(
            name='label',
            options={'verbose_name': 'label', 'verbose_name_plural': 'labels'},
        ),
        migrations.AlterModelOptions(
            name='labelrelation',
            options={'verbose_name': 'label relation', 'verbose_name_plural': 'label relations'},
        ),
        migrations.AlterModelOptions(
            name='labelreview',
            options={'verbose_name': 'label review', 'verbose_name_plural': 'label reviews'},
        ),
        migrations.AlterModelOptions(
            name='level',
            options={'verbose_name': 'level'},
        ),
        migrations.AlterModelOptions(
            name='marker',
            options={'verbose_name': 'marker', 'verbose_name_plural': 'markers'},
        ),
        migrations.AlterModelOptions(
            name='markeraction',
            options={'verbose_name': 'marker action', 'verbose_name_plural': 'marker actions'},
        ),
        migrations.AlterModelOptions(
            name='markercontextmenuitem',
            options={'verbose_name': 'marker context menu item', 'verbose_name_plural': 'marker context menu items'},
        ),
        migrations.AlterModelOptions(
            name='markerpair',
            options={'verbose_name': 'marker pair', 'verbose_name_plural': 'marker pairs'},
        ),
        migrations.AlterModelOptions(
            name='markerrestriction',
            options={'verbose_name': 'marker restriction', 'verbose_name_plural': 'marker restrictions'},
        ),
        migrations.AlterModelOptions(
            name='markerunit',
            options={'verbose_name': 'marker unit', 'verbose_name_plural': 'marker units'},
        ),
        migrations.AlterModelOptions(
            name='markervariant',
            options={'verbose_name': 'marker variant'},
        ),
        migrations.AlterModelOptions(
            name='postprocessingmethod',
            options={'verbose_name': 'post-processing method', 'verbose_name_plural': 'post-processing methods'},
        ),
        migrations.AlterModelOptions(
            name='premarker',
            options={'verbose_name': 'pre-marker', 'verbose_name_plural': 'pre-markers'},
        ),
        migrations.AlterModelOptions(
            name='project',
            options={'verbose_name': 'project', 'verbose_name_plural': 'projects'},
        ),
        migrations.AlterModelOptions(
            name='projectdata',
            options={'verbose_name': 'project datum', 'verbose_name_plural': 'project data'},
        ),
        migrations.AlterModelOptions(
            name='relation',
            options={'verbose_name': 'relation', 'verbose_name_plural': 'relations'},
        ),
        migrations.AlterModelOptions(
            name='userprofile',
            options={'verbose_name': 'a project-specific user profile', 'verbose_name_plural': 'project specific user profile'},
        ),
        migrations.RemoveField(
            model_name='marker',
            name='for_task_type',
        ),
        migrations.RemoveField(
            model_name='relation',
            name='for_task_type',
        ),
        migrations.AlterField(
            model_name='batch',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='context',
            name='content',
            field=models.TextField(verbose_name='content'),
        ),
        migrations.AlterField(
            model_name='context',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='datapoint',
            field=models.CharField(help_text='As stored in the original dataset', max_length=64, verbose_name='datapoint ID'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='flags',
            field=models.TextField(default='', help_text='Internal behavior flags', verbose_name='flags'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='is_skipped',
            field=models.BooleanField(help_text='Indicates whether the datapoint was skipped by an annotator', verbose_name='is skipped?'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='is_submitted',
            field=models.BooleanField(help_text='Indicates whether the datapoint was successfully submitted by an annotator', verbose_name='is submitted?'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='project_data',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.projectdata', verbose_name='project data'),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='name',
            field=models.CharField(max_length=50, verbose_name='dataset name'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='post_processing_methods',
            field=models.ManyToManyField(blank=True, to='projects.PostProcessingMethod', verbose_name='post-processing methods'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='source_type',
            field=models.CharField(choices=[('PlainText', 'Plain text'), ('TextFile', 'Plain text file(s)'), ('Json', 'JSON file(s)'), ('TextsAPI', 'API')], max_length=10, verbose_name='dataset type'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='spec',
            field=models.TextField(help_text='in a JSON format', verbose_name='specification'),
        ),
        migrations.AlterField(
            model_name='input',
            name='content',
            field=models.TextField(verbose_name='content'),
        ),
        migrations.AlterField(
            model_name='input',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='input',
            name='unit',
            field=models.PositiveIntegerField(default=1, help_text='At the submission time', verbose_name='marker group order in the unit'),
        ),
        migrations.AlterField(
            model_name='label',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='label',
            name='end',
            field=models.PositiveIntegerField(help_text='Character-wise end position in the text', null=True, verbose_name='end position'),
        ),
        migrations.AlterField(
            model_name='label',
            name='extra',
            field=models.JSONField(blank=True, help_text='in a JSON format', null=True, verbose_name='extra information'),
        ),
        migrations.AlterField(
            model_name='label',
            name='start',
            field=models.PositiveIntegerField(help_text='Character-wise start position in the text', null=True, verbose_name='start position'),
        ),
        migrations.AlterField(
            model_name='label',
            name='undone',
            field=models.BooleanField(default=False, help_text="Indicates whether the annotator used 'Undo' button", verbose_name='was undone?'),
        ),
        migrations.AlterField(
            model_name='label',
            name='unit',
            field=models.PositiveIntegerField(default=1, help_text='At the submission time', verbose_name='marker group order in the unit'),
        ),
        migrations.AlterField(
            model_name='labelrelation',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='labelrelation',
            name='undone',
            field=models.BooleanField(default=False, help_text="Indicates whether the annotator used 'Undo' button", verbose_name='was undone?'),
        ),
        migrations.AlterField(
            model_name='labelrelation',
            name='unit',
            field=models.PositiveIntegerField(default=1, help_text='At the submission time', verbose_name='marker group order in the unit'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='ambiguity_status',
            field=models.CharField(choices=[('no', 'No ambiguity'), ('rr', 'Requires resolution'), ('rs', 'Resolved')], default='no', help_text='Decided automatically to inform a decision maker', max_length=2, verbose_name='ambiguity?'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='end',
            field=models.PositiveIntegerField(help_text='If applicable', null=True, verbose_name='start position of the review label'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='impossible',
            field=models.BooleanField(default=False, help_text='Indicates whether the reviewer marked the datapoint as impossible wrt. guidelines', verbose_name='is impossible?'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='is_match',
            field=models.BooleanField(help_text='Indicates whether the reviewed and original labels match', null=True, verbose_name='is a match?'),
        ),
        migrations.AlterField(
            model_name='labelreview',
            name='start',
            field=models.PositiveIntegerField(help_text='If applicable', null=True, verbose_name='start position of the review label'),
        ),
        migrations.AlterField(
            model_name='level',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='marker',
            name='code',
            field=models.CharField(blank=True, help_text="Marker's nickname used internally", max_length=25, unique=True, verbose_name='code'),
        ),
        migrations.AlterField(
            model_name='marker',
            name='color',
            field=colorfield.fields.ColorField(default='#FFFFFF', help_text="Marker's color used when annotating the text", max_length=18, verbose_name='color'),
        ),
        migrations.AlterField(
            model_name='marker',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='marker',
            name='name',
            field=models.CharField(help_text='The display name of the marker (max 50 characters)', max_length=50, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='marker',
            name='shortcut',
            field=models.CharField(blank=True, help_text='Keyboard shortcut for annotating a piece of text with this marker', max_length=10, null=True, verbose_name='keyboard shortcut'),
        ),
        migrations.AlterField(
            model_name='markeraction',
            name='admin_filter',
            field=models.CharField(blank=True, help_text="\n            Specifies the filter type in the data explorer interface (one of 'boolean', 'range').\n            If empty, then this action will be excluded from data explorer.\n            ", max_length=50, null=True, verbose_name='type of admin filter'),
        ),
        migrations.AlterField(
            model_name='markeraction',
            name='description',
            field=models.TextField(verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='markeraction',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markeraction',
            name='file',
            field=models.CharField(help_text='a name of the JS plugin file in the `/static/scripts/labeler_plugins` directory', max_length=100, verbose_name='file name'),
        ),
        migrations.AlterField(
            model_name='markeraction',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='action',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.markeraction', verbose_name='marker action'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='config',
            field=models.JSONField(blank=True, null=True, verbose_name='JSON configuration'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='field',
            field=models.CharField(blank=True, help_text='If applicable', max_length=50, null=True, verbose_name='field name in logs'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='verbose',
            field=models.CharField(max_length=50, verbose_name='verbose name'),
        ),
        migrations.AlterField(
            model_name='markercontextmenuitem',
            name='verbose_admin',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='verbose name in data explorer'),
        ),
        migrations.AlterField(
            model_name='markerpair',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markerrestriction',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markerrestriction',
            name='kind',
            field=models.CharField(choices=[('no', '-'), ('ls', '<'), ('le', '<='), ('gs', '>'), ('ge', '>='), ('eq', '=')], max_length=2, verbose_name='restriction kind'),
        ),
        migrations.AlterField(
            model_name='markerrestriction',
            name='value',
            field=models.PositiveIntegerField(help_text="e.g., if restriction kind is '<=' and value is '3', this creates a restriction '<= 3'", verbose_name='restriction value'),
        ),
        migrations.AlterField(
            model_name='markerrestriction',
            name='variant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.markervariant', verbose_name='marker variant'),
        ),
        migrations.AlterField(
            model_name='markerunit',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markerunit',
            name='is_rankable',
            field=models.BooleanField(default=False, help_text='Whether annotators should be allowed to rank units in the annotation batch', verbose_name='is rankable?'),
        ),
        migrations.AlterField(
            model_name='markerunit',
            name='minimum_required',
            field=models.PositiveIntegerField(default=1, help_text="Minimum required number of marker units per annotation batch (can't be more than `size`)", verbose_name='minimum required'),
        ),
        migrations.AlterField(
            model_name='markerunit',
            name='name',
            field=models.CharField(help_text='Internal name for the unit (max 10 characters)', max_length=10, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='markerunit',
            name='size',
            field=models.PositiveIntegerField(default=1, help_text='Default (and maximal) number of marker units per annotation batch', verbose_name='size'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='is_free_text',
            field=models.BooleanField(default=False, help_text='Indicates whether a marker should be instantiated as a label or a free-text input', verbose_name='is a free-text input?'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='marker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.marker', verbose_name='marker'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='order_in_unit',
            field=models.PositiveIntegerField(blank=True, help_text='Order of this marker in the unit', null=True, verbose_name='order in a unit'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='unit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.markerunit', verbose_name='marker unit'),
        ),
        migrations.AlterField(
            model_name='postprocessingmethod',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='postprocessingmethod',
            name='helper',
            field=models.CharField(help_text='Name as specified in `projects/helpers.py`', max_length=50, verbose_name='helper function name'),
        ),
        migrations.AlterField(
            model_name='postprocessingmethod',
            name='name',
            field=models.CharField(help_text='Verbose name', max_length=50, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='premarker',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='premarker',
            name='tokens',
            field=models.TextField(help_text='Comma-separated tokens that should be highlighted with a marker', verbose_name='static tokens'),
        ),
        migrations.AlterField(
            model_name='project',
            name='allow_selecting_labels',
            field=models.BooleanField(default=False, verbose_name='should selecting the labels be allowed?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='author',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='author'),
        ),
        migrations.AlterField(
            model_name='project',
            name='collaborators',
            field=models.ManyToManyField(blank=True, related_name='shared_projects', to=settings.AUTH_USER_MODEL, verbose_name='collaborators'),
        ),
        migrations.AlterField(
            model_name='project',
            name='context_size',
            field=models.CharField(choices=[('no', 'No context'), ('t', 'Text'), ('p', 'Paragraph')], help_text='Context size for storing labels', max_length=2, verbose_name='size of the textual context'),
        ),
        migrations.AlterField(
            model_name='project',
            name='datasources',
            field=models.ManyToManyField(through='projects.ProjectData', to='projects.DataSource', verbose_name='data sources'),
        ),
        migrations.AlterField(
            model_name='project',
            name='disable_submitted_labels',
            field=models.BooleanField(default=True, verbose_name='should submitted labels be disabled?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='disjoint_annotation',
            field=models.BooleanField(default=False, verbose_name='should disjoint annotation be allowed?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='project',
            name='dt_finish',
            field=models.DateTimeField(verbose_name='to be finished at'),
        ),
        migrations.AlterField(
            model_name='project',
            name='dt_publish',
            field=models.DateTimeField(verbose_name='to be published at'),
        ),
        migrations.AlterField(
            model_name='project',
            name='dt_updated',
            field=models.DateTimeField(auto_now=True, verbose_name='updated at'),
        ),
        migrations.AlterField(
            model_name='project',
            name='has_intro_tour',
            field=models.BooleanField(default=False, help_text='WARNING: Intro tours are currently in beta', verbose_name='should the project include intro tour?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='institution',
            field=models.CharField(blank=True, help_text='Institution responsible for the project', max_length=500, null=True, verbose_name='institution'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_open',
            field=models.BooleanField(default=False, verbose_name='should the project be public?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='is_peer_reviewed',
            field=models.BooleanField(default=False, verbose_name='should the annotations be peer reviewed?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='markers',
            field=models.ManyToManyField(blank=True, through='projects.MarkerVariant', to='projects.Marker', verbose_name='project-specific markers'),
        ),
        migrations.AlterField(
            model_name='project',
            name='max_markers_per_input',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='maximal number of markers per input'),
        ),
        migrations.AlterField(
            model_name='project',
            name='participants',
            field=models.ManyToManyField(blank=True, related_name='participations', through='projects.UserProfile', to=settings.AUTH_USER_MODEL, verbose_name='participants'),
        ),
        migrations.AlterField(
            model_name='project',
            name='points_scope',
            field=models.CharField(choices=[('n', 'No points'), ('i', 'Per input'), ('l', 'Per label')], help_text='The scope of the submitted task', max_length=2, verbose_name='points scope'),
        ),
        migrations.AlterField(
            model_name='project',
            name='points_unit',
            field=models.PositiveIntegerField(default=1, help_text='Number of points per submitted task', verbose_name="points' unit"),
        ),
        migrations.AlterField(
            model_name='project',
            name='round_length',
            field=models.PositiveIntegerField(blank=True, help_text='The number of text snippets consituting one round of the game', null=True, verbose_name='round length'),
        ),
        migrations.AlterField(
            model_name='project',
            name='sampling_with_replacement',
            field=models.BooleanField(default=False, verbose_name='should data be sampled with replacement?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='short_description',
            field=models.TextField(default='', help_text='Will be displayed on the project card', max_length=1000, verbose_name='short description'),
        ),
        migrations.AlterField(
            model_name='project',
            name='show_dataset_identifiers',
            field=models.BooleanField(default=False, verbose_name='should dataset identifiers be shown?'),
        ),
        migrations.AlterField(
            model_name='project',
            name='supported_by',
            field=models.CharField(blank=True, help_text='The name of the organization supporting the project financially (if applicable)', max_length=1000, null=True, verbose_name='supported by'),
        ),
        migrations.AlterField(
            model_name='project',
            name='task_type',
            field=models.CharField(choices=[('qa', 'Question Answering'), ('ner', 'Named Entity Recognition'), ('corr', 'Coreference Resolution'), ('generic', 'Generic'), ('ranking', 'Ranking')], max_length=10, verbose_name='type of the annotation task'),
        ),
        migrations.AlterField(
            model_name='project',
            name='title',
            field=models.CharField(max_length=50, verbose_name='title'),
        ),
        migrations.AlterField(
            model_name='project',
            name='video_summary',
            field=filebrowser.fields.FileBrowseField(blank=True, help_text='Video introducing people to the annotation task at hand (if applicable)', max_length=1000, null=True, verbose_name='summary video'),
        ),
        migrations.AlterField(
            model_name='projectdata',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='direction',
            field=models.CharField(choices=[('0', 'Directed from the first to the second'), ('1', 'Directed from the second to the first'), ('2', 'Bi-directional')], max_length=1, verbose_name='direction'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='name',
            field=models.CharField(max_length=50, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='pairs',
            field=models.ManyToManyField(to='projects.MarkerPair', verbose_name='marker pairs'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='representation',
            field=models.CharField(choices=[('g', 'Graph'), ('l', 'List')], default='g', help_text='How should the relation be visualized?', max_length=1, verbose_name='graphical representation type'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='shortcut',
            field=models.CharField(blank=True, help_text='Keyboard shortcut for marking a piece of text with this relation', max_length=15, null=True, verbose_name='keyboard shortcut'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='dt_created',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='Autofilled', null=True, verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='points',
            field=models.FloatField(default=0.0, verbose_name='points in total'),
        ),
    ]
