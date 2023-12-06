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
