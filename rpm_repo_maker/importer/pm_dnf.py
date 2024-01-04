from .base import RPMRepoImporter


class DnfRepoImporter(RPMRepoImporter):
    """DnfRepoImporter
    Tested on CentOS

    Import a dnf repository archive to an offline machine.
    """

    DESC_DISTRO = 'CentOS'
    SHELL_ALIAS = 'dnf-off'
    SHELL_ALIAS_CMD = 'dnf --disablerepo=\\* --enablerepo={name}'

    logger = RPMRepoImporter.logger.getChild("dnf")
