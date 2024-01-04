# coding: utf-8

import os

from ..config import ROOT_LOGGER
from ..helper import run, cmd_exists, FileEditor


class RPMRepoImporter(object):
    """RPMRepoImporter"""

    DESC_DISTRO = 'CentOS'
    REPO_PATH = '/etc/yum.repos.d'
    SHELL_CONFIG_PATH = '~/.bashrc'
    SHELL_ALIAS = ''
    SHELL_ALIAS_CMD = ''

    logger = ROOT_LOGGER.getChild("importer")

    def __init__(self, name, path, desc_name=None, file_name=None):
        self.name = name
        self.path = os.path.abspath(path)
        self.repo = None
        self.desc_name = desc_name
        self.file_name = file_name

    def prepare(self):
        # check
        if not os.path.isdir(self.repo):
            raise ValueError("path is not a valid directory: {}".format(self.repo))
        if not os.path.isfile(self.path):
            raise ValueError("path is not a valid file: {}".format(self.path))
        if not self.path.endswith('.tar.gz'):
            raise ValueError("path is not a valid archive: {}".format(self.path))

        cmds = ['rpm', 'tar']
        for cmd in cmds:
            if not cmd_exists(cmd):
                raise ValueError("command not found: {}".format(cmd))

        if self.desc_name is None:
            self.desc_name = "{}-$releasever - {}".format(self.DESC_DISTRO, self.name)
        if self.file_name is None:
            self.file_name = self.get_file_name()

    def get_file_name(self):
        name_list = self.name.split('-')
        if 'offline' in name_list:
            name_list.remove('offline')
        return ''.join(name_list).upper()

    def make(self):
        run("tar -C {} -zxf {}".format(self.repo, self.path))
        cmd = """[{name}]
name={desc_name}
baseurl=file://{path}/{name}
enabled=0
gpgcheck=0
"""

        with open(os.path.join(self.REPO_PATH, "{}.repo".format(self.file_name)), 'w') as f:
            f.write(cmd.format(
                name=self.name,
                path=self.repo,
                desc_name=self.desc_name,
            ))

    def generate_alias(self):
        if self.SHELL_ALIAS and self.SHELL_ALIAS_CMD:
            editor = FileEditor(self.SHELL_CONFIG_PATH)
            alias = u"alias {}='{}'".format(
                self.SHELL_ALIAS,
                self.SHELL_ALIAS_CMD.format(name=self.name),
            )
            editor.ensure_lines('# offline repository alias', alias)
            editor.save()

    def cleanup(self):
        pass

    def __call__(self, repo):
        self.repo = repo
        self.prepare()
        try:
            self.make()
        except Exception as e:
            self.cleanup()
            raise e
        else:
            self.generate_alias()
            self.cleanup()

