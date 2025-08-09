from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Setup site for django-allauth'

    def handle(self, *args, **options):
        # Update the default site
        site = Site.objects.get(pk=1)
        site.domain = 'localhost:8000'
        site.name = 'Knowledge Engine'
        site.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated site: {site.name} ({site.domain})'
            )
        )