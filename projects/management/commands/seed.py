from django.core.management.base import BaseCommand
import random

# python manage.py seed --mode=refresh

""" Clear all data and creates addresses """
MODE_REFRESH = 'refresh'

""" Clear all data and do not create any object """
MODE_CLEAR = 'clear'


class Command(BaseCommand):
    help = "seed database for testing and development."

    def add_arguments(self, parser):
        parser.add_argument('--mode', type=str, help="Mode")

    def handle(self, *args, **options):
        self.stdout.write('seeding data...')
        run_seed(self, options['mode'])
        self.stdout.write('done.')


def clear_data():
    """Deletes all the table data"""
    logger.info("Delete Marker instances")
    Marker.objects.all().delete()


def create_markers():
    """Creates an address object combining different elements from the list"""
    logger.info("Creating markers for out-of-the-box annotation tasks")

    # name = models.CharField(max_length=50, unique=True,
    #     help_text="The display name of the marker (max 50 characters, must be unique)")
    # short = models.CharField(max_length=10, unique=True, blank=True,
    #     help_text="""Marker's nickname used internally (max 10 characters, must be unique,
    #                  by default the capitalized first three character of the label)""")
    # color = ColorField(help_text="Marker's color used when annotating the text")
    # for_task_type = models.CharField(max_length=10, choices=settings.TASK_TYPES, blank=True,
    #     help_text="Specify task types (if any) for which this marker must be present (avaiable only to admins)")
    # shortcut = models.CharField(max_length=10, null=True, blank=True,
    #     help_text="Keyboard shortcut for annotating a piece of text with this marker")
    # actions = models.ManyToManyField(MarkerAction, through='MarkerContextMenuItem', blank=True,
    #     help_text="Actions associated with each marker [EXPAND]")
    specs = [
        {
            'name': "Correct answer",
            "color": "#48c774",
            "for_task_type": "qa",
            "shortcut": "A"
        },
        {
            'name': "Distractor",
            "color": "#f14668"
            "for_task_type": "qa",
            "shortcut": "D"
        },
        
    ]

    
    logger.info("{} address created.".format(address))


def run_seed(self, mode):
    """ Seed database based on mode

    :param mode: refresh / clear 
    :return:
    """
    # Clear data from tables
    clear_data()
    if mode == MODE_CLEAR:
        return

    create_markers()
