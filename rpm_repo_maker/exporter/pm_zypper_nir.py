import os
import shutil
import tempfile

from .finder import PackageFinderV2
from ..config import ROOT_LOGGER
from ..helper import run, lcd, cmd_exists


class ZypperNIRPackageFinder(PackageFinderV2):
    logger = PackageFinderV2.logger.getChild("zypper")

    @classmethod
    def _ensure_repo_source(cls):
        """Install repository related tools, add extra online yum repository."""
        cls.logger.info("Extra zypper repository should be add manually ...")

        run("zypper install -y createrepo")

    @classmethod
    def _get_rpm_dependency_version(cls, pkg_item_list):
        """Get latest full dependency package list from yum by a package item list.
        Support multiple versions of same package.
        """
        results = []
        # package item
        for pkg_item in pkg_item_list:
            results.append(pkg_item['name'])

        results.sort()
        return results



class ZypperNIRRepoExporter:
    """Zypper repo exporter when --installroot option is not available.
    """

    TEMP_DIR_PREFIX = 'repomaker'

    logger = ROOT_LOGGER.getChild('exporter')

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
        cmds = ['tar']
        for cmd in cmds:
            if not cmd_exists(cmd):
                raise ValueError("command not found: {}".format(cmd))

    def make(self, pkg_list):
        """
        # fake a install root
        mkdir -p /opt/rootfs/etc
        mkdir -p /opt/rootfs/var/lib/rpm
        cp -a /etc/zypp /opt/rootfs/etc/
        cp -a /var/lib/rpm /opt/rootfs/var/lib/

        # chroot
        zypper -R /opt/rootfs --no-cd --gpg-auto-import-keys install --auto-agree-with-licenses -y -d docker

        # create repo
        zypper install createrepo
        createrepo --database /tmp/$PKG
        rm -rf /tmp/$PKG-installroot
        """
        # fake a rootfs
        self.logger.info("Faking root file system ...")
        installroot = os.path.join(self.tempdir, 'installroot')
        etc_path = os.path.join(installroot, 'etc')
        rpm_lib_path = os.path.join(installroot, 'var', 'lib', 'rpm')
        run("mkdir -p {}".format(etc_path))
        run("mkdir -p {}".format(rpm_lib_path))
        run("cp -a /etc/zypp {}".format(etc_path))
        run("cp -a /var/lib/rpm {}".format(etc_path))

        # download
        for pkg in pkg_list:
            self.logger.info("Downloading package {} ...".format(pkg))
            run("zypper -R {} --no-cd --gpg-auto-import-keys install --auto-agree-with-licenses -y -d {}".format(
                installroot, pkg))

        # collect downloaded
        cachedir = os.path.join(installroot, 'var', 'cache', 'zypp', 'packages')
        downloaddir = os.path.join(self.tempdir, self.name)
        run("mkdir -p {}".format(downloaddir))
        run("cp -a {}/*/* {}".format(cachedir, downloaddir))

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
