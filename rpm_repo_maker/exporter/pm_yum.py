# coding: utf-8

import os
import shutil
import platform
import tempfile

from .finder import PackageFinder
from ..config import ROOT_LOGGER
from ..helper import run, lcd, cmd_exists


class YumPackageFinder(PackageFinder):

    logger = PackageFinder.logger.getChild("yum")

    @classmethod
    def _is_repo_enabled(cls, repo):
        """Return true if repo exists and enabled, else return false."""
        stdout = run("yum-config-manager --enable {}".format(repo))
        repo_title = "=== repo: {} ===".format(repo)
        return repo_title in stdout

    @classmethod
    def _ensure_repo_source(cls):
        """Install repository related tools, add extra online yum repository."""
        cls.logger.info("Adding extra yum online repositories ...")

        run("yum install -y epel-release yum-plugin-downloadonly yum-utils createrepo")
        # ensure repo
        if not cls._is_repo_enabled("docker-ce-stable"):
            run("yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo")

    @classmethod
    def _parse_pkg_list(cls, pkg_list):
        pkg_item_list = []
        for pkg in pkg_list:
            if isinstance(pkg, (str, unicode)):
                pkg_item_list.append({'name': pkg})
            elif isinstance(pkg, dict):
                pkg_item_list.append(pkg)
            elif isinstance(pkg, (list, tuple)):
                pkg_item_list.extend(cls._parse_pkg_list(pkg))
            else:
                raise ValueError("unknown type of value", pkg)
        return pkg_item_list


    @classmethod
    def _get_pkg_deps(cls, pkg_obj):
        import yum

        yb = yum.YumBase()
        yb.install(pkg_obj)
        yb.resolveDeps()
        deps = set(yb.tsInfo._namedict.keys())
        if pkg_obj.name in deps:
            deps.remove(pkg_obj.name)
        deps.add("{}-{}".format(pkg_obj.name, pkg_obj.version))
        return deps

    @classmethod
    def _get_rpm_dependency_alter(cls, pkg_name_list):
        """Get latest full dependency package list from yum by a package name list."""
        import yum

        cls._ensure_repo_source()

        yb = yum.YumBase()
        dep_pkgs = set()

        # package name
        for pkg_name in pkg_name_list:
            try:
                yb.install(name=pkg_name)
            except Exception:
                traceback.print_exc()
                cls.logger.error("install package error: {}".format(pkg_name))
                sys.exit(3)

        yb.resolveDeps()

        dep_pkgs = set(yb.tsInfo._namedict.keys())
        dep_pkgs.update(pkg_name_list)

        results = list(dep_pkgs)
        results.sort()
        return results

    @classmethod
    def _get_rpm_dependency_version(cls, pkg_item_list):
        """Get latest full dependency package list from yum by a package item list.
        Support multiple versions of same package.
        """
        import yum

        cls._ensure_repo_source()

        yb = yum.YumBase()
        dep_pkgs = set()

        # package item
        for pkg_item in pkg_item_list:
            avai_pkg_list = yb.pkgSack.searchNames([pkg_item['name']])
            if len(avai_pkg_list) <= 0:
                raise ValueError("package not found", pkg_item)

            # select packages
            pkgs = cls._select_packages(pkg_item, avai_pkg_list)
            for pkg in pkgs:
                deps = cls._get_pkg_deps(pkg)
                dep_pkgs.update(deps)

        results = list(dep_pkgs)
        results.sort()
        return results


class YumRepoExporter(object):
    """YumRepoExporter
    Tested on CentOS 7

    Export yum repository into an archive from an online machine.
    """

    TEMP_DIR_PREFIX = 'repomaker'

    logger = ROOT_LOGGER.getChild("exporter")

    def __init__(self, name, path=None, platform_suffix=None):
        self.name = name
        self.path = os.path.abspath(path)
        self.platform_suffix = platform_suffix
        self.tempdir = tempfile.mkdtemp(prefix="{}-".format(self.TEMP_DIR_PREFIX))

    def prepare(self):
        # check
        if not os.path.exists(self.path):
            raise ValueError("path not exist: {}".format(self.path))
        if not os.path.isdir(self.path):
            raise ValueError("path is not a valid directory: {}".format(self.path))
        if self.path is None:
            self.path = os.path.abspath(os.getcwd())
        cmds = ['yum', 'tar']
        for cmd in cmds:
            if not cmd_exists(cmd):
                raise ValueError("command not found: {}".format(cmd))

    def make(self, pkg_list):
        """
        PKG="offline"
        yum install --downloadonly --installroot=/tmp/$PKG-installroot --releasever=7 --downloaddir=/tmp/$PKG
        createrepo --database /tmp/$PKG
        rm -rf /tmp/$PKG-installroot
        """
        installroot = os.path.join(self.tempdir, 'installroot')
        downloaddir = os.path.join(self.tempdir, self.name)
        distro = platform.linux_distribution()
        releasever = distro[1].split('.')[0]
        for pkg in pkg_list:
            self.logger.info("Downloading package {} ...".format(pkg))
            run("yum install --downloadonly --installroot={} --releasever={} --downloaddir={} {}".format(
                installroot, releasever, downloaddir, pkg))

        # createrepo
        self.logger.info("Creating repository ...")
        run("createrepo --database {}".format(downloaddir))

        # archive it
        self.logger.info("Making archive ...")
        with lcd(self.tempdir):
            run("tar -zcf {name}.tar.gz {name}".format(name=self.name))
        tarfile = "{}.tar.gz".format(self.name)
        tarpath = os.path.join(self.tempdir, "{}".format(tarfile))

        # generate target tar file
        target_tarfile = "{}.tar.gz".format(self.name)
        if self.platform_suffix:
            target_tarfile = "{}.{}.tar.gz".format(self.name, self.platform_suffix)
        target_tarpath = os.path.join(self.path, target_tarfile)

        # delete old and move new
        if os.path.isfile(target_tarpath):
            os.remove(target_tarpath)
        shutil.move(tarpath, target_tarpath)

    def cleanup(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def __call__(self, pkg_list):
        self.prepare()

        self.logger.info("Exporter's temp directory is {}".format(self.tempdir))
        try:
            self.make(pkg_list)
        except Exception as e:
            self.cleanup()
            raise e
        else:
            self.cleanup()
