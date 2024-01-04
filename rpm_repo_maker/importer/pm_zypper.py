# coding: utf-8

from .base import RPMRepoImporter


class ZypperSLESRepoImporter(RPMRepoImporter):
    """ZypperSLESRepoImporter
    Import a rpm repository archive to an offline machine.
    """

    DESC_DISTRO = 'SLES'
    REPO_PATH = '/etc/zypp/repos.d'
    SHELL_ALIAS = 'zypper-off'
    SHELL_ALIAS_CMD = 'zypper --no-cd --plus-content {name}'

    logger = RPMRepoImporter.logger.getChild("zypper")
