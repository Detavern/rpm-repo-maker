from .base import RPMRepoImporter


class DnfRepoImporter(RPMRepoImporter):
    """DnfRepoImporter
    Tested on CentOS

    Import a dnf repository archive to an offline machine.
    """

    DESC_DISTRO = 'CentOS'

    logger = RPMRepoImporter.logger.getChild("dnf")
