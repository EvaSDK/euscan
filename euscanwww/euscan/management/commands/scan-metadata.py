import subprocess
import portage
import sys
import os
import re

from portage import versions
from optparse import make_option

from django.db.transaction import commit_on_success
from django.core.management.base import BaseCommand, CommandError
from euscanwww.euscan.models import Package, Herd, Maintainer

from gentoolkit.query import Query
from gentoolkit.eclean.search import (port_settings)

class Command(BaseCommand):
    _overlays = {}

    option_list = BaseCommand.option_list + (
        make_option('--all',
            action='store_true',
            dest='all',
            default=False,
            help='Scan all packages'),
        make_option('--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='Be quiet'),
        )
    args = '<package package ...>'
    help = 'Scans metadata and fills database'

    def handle(self, *args, **options):
        if len(args) == 0 and options['all'] == False:
            raise CommandError('You must specify a package or use --all')

        if not options['quiet']:
            self.stdout.write('Scanning portage tree...\n')

        if len(args) == 0:
            for pkg in Package.objects.all():
                self.scan(options, '%s/%s' % (pkg.category, pkg.name))
        else:
            for package in args:
                self.scan(options, package)

        if not options['quiet']:
            self.stdout.write('Done.\n')

    @commit_on_success
    def scan(self, options, query=None):
        matches = Query(query).find(
                include_masked=True,
                in_installed=False
        )

        if not matches:
                sys.stderr.write(self.style.ERROR("Unknown package '%s'\n" % query))
                return

	matches = sorted(matches)
        pkg = matches.pop()
	if pkg.version == '9999':
		pkg = matches.pop()

        obj, created = Package.objects.get_or_create(category=pkg.category, name=pkg.name)

        obj.homepage = pkg.environment("HOMEPAGE")
        obj.description = pkg.environment("DESCRIPTION")

        for herd in pkg.metadata.herds(True):
            herd = self.store_herd(options, herd[0], herd[1])
            obj.herds.add(herd)

        for maintainer in pkg.metadata.maintainers():
            maintainer = self.store_maintainer(options, maintainer.name, maintainer.email)
            obj.maintainers.add(maintainer)

        if not options['quiet']:
            sys.stdout.write('[p] %s/%s\n' % (pkg.category, pkg.name))

        obj.save()

    def store_herd(self, options, name, email):
        herd, created = Herd.objects.get_or_create(herd=name)

        if created or herd.email != email:
            if not options['quiet']:
                sys.stdout.write('[h] %s <%s>\n' % (name, email))

            herd.email = email
            herd.save()

        return herd

    def store_maintainer(self, options, name, email):
        if not name:
            name = email

        maintainer, created = Maintainer.objects.get_or_create(name=name, email=email)

        if created:
            if not options['quiet']:
                sys.stdout.write('[m] %s <%s>\n' % (name.encode('utf-8'), email))

            maintainer.save()

        return maintainer