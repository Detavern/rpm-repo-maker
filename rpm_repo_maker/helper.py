# coding: utf-8

import os
import sys
import subprocess

from .config import ENV, PROJ_DIR, ROOT_LOGGER

logger = ROOT_LOGGER.getChild("helper")


def run(cmd, suppress=False):
    """shell=True is dangerous, but it's fine to use here.
    """
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        if suppress:
            return out, err
        else:
            logger.info("stdout: {}".format(out))
            logger.error("stderr: {}".format(err))
            sys.exit(3)
    else:
        if out and ENV == 'dev':
            logger.debug("stdout: {}".format(out))
        return out


def move(src, dst, mode=None):
    """copy move"""
    suffix = src.split("/")[-1]
    if os.path.isdir(src):
        run("cp -rp {} {}".format(src, dst))
        if mode:
            run("chmod -R {} {}".format(mode, dst + "/" + suffix))
    else:
        run("cp {} {}".format(src, dst))
        if mode:
            run("chmod {} {}".format(mode, dst))


def cmd_exists(cmd, path=None):
    """check executable exist or not"""
    if path is None:
        path = os.environ["PATH"].split(os.pathsep)

    for prefix in path:
        filename = os.path.join(prefix, cmd)
        executable = os.access(filename, os.X_OK)
        is_not_directory = os.path.isfile(filename)
        if executable and is_not_directory:
            return True
    return False


class lcd(object):
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(PROJ_DIR)


class FileEditor(object):
    def __init__(self, fp):
        self._fp = fp
        self._lines = None
        self._content = self.try_read(self._fp)
        self._modified = False

    def try_read(self, path):
        fp = os.path.expanduser(path)
        if os.path.isfile(fp):
            with open(fp, 'rb') as f:
                return f.read().decode('utf-8')
        else:
            return u''

    @property
    def lines(self):
        if self._lines is None:
            self._lines = self._content.split('\n')
        return self._lines
    
    def append_lines(self, *lines):
        if not self._modified:
            self._modified = True
        self._lines.extend(lines)

    def ensure_lines(self, *lines):
        for line in lines:
            if line in self.lines:
                return
            self.append_lines(line)

    def save(self):
        fp = os.path.expanduser(self._fp)
        if self._modified:
            with open(fp, 'wb') as f:
                f.write(u'\n'.join(self.lines).encode('utf-8'))
