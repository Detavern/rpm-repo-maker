from .base import RPMRepoImporter
from .pm_dnf import DnfRepoImporter


class DnfKylinRepoImporter(DnfRepoImporter):
    DESC_DISTRO = 'Kylin'

    logger = RPMRepoImporter.logger.getChild("dnf-kylin")
