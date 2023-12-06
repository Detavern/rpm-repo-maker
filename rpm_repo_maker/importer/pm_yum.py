# coding: utf-8

from .base import RPMRepoImporter


class YumRepoImporter(RPMRepoImporter):
    """YumRepoImporter
    Tested on CentOS

    Import a rpm repository archive to an offline machine.
    """

    DESC_DISTRO = 'CentOS'

    logger = RPMRepoImporter.logger.getChild("yum")
