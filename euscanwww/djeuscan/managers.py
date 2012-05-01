"""
djeuscan.managers
"""

from django.db import models
from djeuscan.helpers import xint


class PackageManager(models.Manager):
    def n_packaged(self):
        res = self.aggregate(models.Sum('n_packaged'))['n_packaged__sum']
        return xint(res)

    def n_overlay(self):
        res = self.aggregate(models.Sum('n_overlay'))['n_overlay__sum']
        return xint(res)

    def n_versions(self):
        res = self.aggregate(models.Sum('n_versions'))['n_versions__sum']
        return xint(res)

    def n_upstream(self):
        return self.n_versions() - self.n_packaged() - self.n_overlay()

    def categories(self):
        return self.values('category').annotate(
            n_packaged=models.Sum('n_packaged'),
            n_overlay=models.Sum('n_overlay'),
            n_versions=models.Sum('n_versions')
        )

    def herds(self):
        # FIXME: optimize the query, it uses 'LEFT OUTER JOIN' instead of
        # 'INNER JOIN'
        res = self.filter(herds__isnull=False)
        res = res.values('herds__herd').annotate(
            n_packaged=models.Sum('n_packaged'),
            n_overlay=models.Sum('n_overlay'),
            n_versions=models.Sum('n_versions')
        )
        return res

    def maintainers(self):
        res = self.filter(maintainers__isnull=False).values(
            'maintainers__id', 'maintainers__name', 'maintainers__email'
        )
        res = res.annotate(
            n_packaged=models.Sum('n_packaged'),
            n_overlay=models.Sum('n_overlay'),
            n_versions=models.Sum('n_versions')
        )
        return res

    def overlays(self):
        res = self.values('version__overlay').exclude(version__overlay='')
        return res.distinct()