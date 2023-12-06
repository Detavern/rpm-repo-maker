from .finder import PackageFinder
from .pm_dnf import DnfPackageFinder

from ..helper import run


class DnfKylinPackageFinder(DnfPackageFinder):
    logger = PackageFinder.logger.getChild("dnf-kylin")

    @classmethod
    def _ensure_repo_source(cls):
        """Install repository related tools, add extra online yum repository."""
        cls.logger.info("Adding Kylin online repositories ...")
        repo_str = """[kcnos]
name=Kylin-$releasever - kcnos - archive.kylinos.cn
baseurl=https://archive.kylinos.cn/yum/v10/kcnos/stable/V10.20231030.3.0/$basearch/
gpgcheck=0
"""
        # ensure repo
        if not cls._is_repo_enabled("kcnos"):
            run("mv /etc/yum.repos.d /etc/yum.repos.d.bak")
            run("mkdir -p /etc/yum.repos.d")
            with open('/etc/yum.repos.d/kcnos.repo', 'w') as f:
                f.write(repo_str)
            run("dnf makecache")

    @classmethod
    def _get_pkg_deps(cls, pkg_obj):
        import dnf

        with dnf.Base() as db:
            db.read_all_repos()
            db.fill_sack()

            db.package_install(pkg_obj)
            db.resolve()
            # import ipdb; ipdb.set_trace()
            deps = {pkg.name for pkg in db.transaction.install_set}
            if pkg_obj.name in deps:
                deps.remove(pkg_obj.name)
            deps.add("{}-{}".format(pkg_obj.name, pkg_obj.version))
        return deps

    @classmethod
    def _get_rpm_dependency_version(cls, pkg_item_list):
        """Get latest full dependency package list from yum by a package item list.
        Support multiple versions of same package.
        """
        import dnf

        dep_pkgs = set()
        with dnf.Base() as db:
            db.read_all_repos()
            db.fill_sack()
            # import ipdb; ipdb.set_trace()

            # package item
            for pkg_item in pkg_item_list:
                q = db.sack.query().filter(name=pkg_item['name'])
                avai_pkg_list = list(q)
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
