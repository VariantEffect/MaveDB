import sys
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import News

LEVELS = [i[0] for i in News.STATUS_CHOICES]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--message',
            type=str,
            help="Announcemnet message string or file (markdown supported)",
        )
        parser.add_argument(
            '--level',
            type=str,
            help="Message level ({})".format(', '.join(LEVELS)),
        )
    
    @transaction.atomic
    def handle(self, *args, **kwargs):
        message = kwargs.get('message')
        level = kwargs.get('level')
        
        path = os.path.normpath(os.path.expanduser(message))
        if not message:
            sys.stderr.write("Please supply a message.\n")
            sys.exit()
            
        if os.path.isfile(path):
            message = open(path, 'rt').read()
            if not message:
                sys.stderr.write("Please supply a message.\n")
                sys.exit()
                
        if level not in LEVELS:
            sys.stderr.write("Unsupported level {}.\n".format(level))
            sys.exit()
        
        News.objects.create(text=message, level=level)
        sys.stdout.write("Created news item.")
