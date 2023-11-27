# coding: utf-8

import os
import sys
import shutil
import platform
import tempfile
import traceback

from .config import ROOT_LOGGER

from .helper import run, lcd, cmd_exists


def yum_packages_handler_latest(yum_pkg_list):
    # TODO: better latest
    return yum_pkg_list[-1]


class YumPackageFinder(object):
    SPECIAL_VERSION_META = "@"
    SPECIAL_VERSION_TAG_LATEST = "{}latest".format(SPECIAL_VERSION_META)
    SPECIAL_VERSION_HANDLERS = {
        SPECIAL_VERSION_TAG_LATEST: yum_packages_handler_latest,
    }

    logger = ROOT_LOGGER.getChild("finder")

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
    def _select_packages(cls, pkg_item, yum_pkg_list):
        """Select multiple yum packages by versions."""
        # merge version & versions
        ver = pkg_item.get('version', cls.SPECIAL_VERSION_TAG_LATEST)
        if not pkg_item.get('versions'):
            pkg_item['versions'] = [ver]
        cls.logger.debug("request package item is: {}".format(pkg_item))

        # generate yum package map
        yum_pkg_map = {}
        for pkg in yum_pkg_list:
            yum_pkg_map[pkg.version] = pkg

        # select version
        selected_pkgs = []
        for version in pkg_item['versions']:
            if version in cls.SPECIAL_VERSION_HANDLERS:
                res = cls.SPECIAL_VERSION_HANDLERS[version](yum_pkg_list)
                if res is None:
                    cls.logger.warning("package {}'s special version tag {} does not select any item!".format(
                        pkg_item['name'], version))
                elif isinstance(res, list):
                    selected_pkgs.extend(res)
                else:
                    selected_pkgs.append(res)
                continue
            if version in yum_pkg_map:
                selected_pkgs.append(yum_pkg_map[version])
                continue
            raise ValueError("unknown version of package {}: {}".format(pkg_item['name'], version))

        if not selected_pkgs:
            raise ValueError("package {} does not select any item!".format(pkg_item['name']))
        cls.logger.info("selected {} packages are {}".format(
            pkg_item['name'], [pkg.version for pkg in selected_pkgs]))
        return selected_pkgs

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
    def _get_yum_dependency_alter(cls, pkg_name_list):
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
    def _get_yum_dependency_version(cls, pkg_item_list):
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
    def get_yum_dependency(cls, pkg_list):
        """Get latest full dependency package list from yum by a package list."""
        pkg_item_list = cls._parse_pkg_list(pkg_list)
        return cls._get_yum_dependency_version(pkg_item_list)


class YumRepoExporter(object):
    """YumRepoExporter
    For CentOS

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


class YumRepoImporter(object):
    """YumRepoImporter
    For CentOS

    Import a yum repository archive to an offline machine.
    """

    def __init__(self, name, path, desc_name=None, file_name=None, gpg_key=None):
        self.logger = ROOT_LOGGER.getChild("importer")
        self.name = name
        self.path = os.path.abspath(path)
        self.repo = None
        self.desc_name = desc_name
        self.file_name = file_name
        self.gpg_key = gpg_key

    def prepare(self):
        # check
        if not os.path.isdir(self.repo):
            raise ValueError("path is not a valid directory: {}".format(self.repo))
        if not os.path.isfile(self.path):
            raise ValueError("path is not a valid file: {}".format(self.path))
        if not self.path.endswith('.tar.gz'):
            raise ValueError("path is not a valid archive: {}".format(self.path))

        rpm_gpg_key = "/etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7"
        if not os.path.exists(rpm_gpg_key):
            raise FileNotFoundError("could not found rpm gpg key")

        cmds = ['yum', 'tar']
        for cmd in cmds:
            if not cmd_exists(cmd):
                raise ValueError("command not found: {}".format(cmd))

        if self.desc_name is None:
            self.desc_name = "CentOS-7 - {}".format(self.name)
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
"""
        # set gpg
        if self.gpg_key is None:
            cmd += "gpgcheck=0\n"
        else:
            cmd += """gpgcheck=1
gpgkey=file://{path}
""".format(path=os.path.abspath(self.gpg_key))

        with open("/etc/yum.repos.d/{}.repo".format(self.file_name), 'w') as f:
            f.write(cmd.format(
                name=self.name,
                path=self.repo,
                desc_name=self.desc_name,
            ))

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
            self.cleanup()



