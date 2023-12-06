from ..config import ROOT_LOGGER


def rpm_packages_handler_latest(rpm_pkg_list):
    # TODO: better latest
    return rpm_pkg_list[-1]


class PackageFinder(object):
    SPECIAL_VERSION_META = "@"
    SPECIAL_VERSION_TAG_LATEST = "{}latest".format(SPECIAL_VERSION_META)
    SPECIAL_VERSION_HANDLERS = {
        SPECIAL_VERSION_TAG_LATEST: rpm_packages_handler_latest,
    }

    logger = ROOT_LOGGER.getChild("finder")

    @classmethod
    def _select_packages(cls, pkg_item, rpm_pkg_list):
        """Select multiple rpm packages by versions."""
        # merge version & versions
        ver = pkg_item.get('version', cls.SPECIAL_VERSION_TAG_LATEST)
        if not pkg_item.get('versions'):
            pkg_item['versions'] = [ver]
        cls.logger.debug("request package item is: {}".format(pkg_item))

        # generate rpm package map
        rpm_pkg_map = {}
        for pkg in rpm_pkg_list:
            rpm_pkg_map[pkg.version] = pkg

        # select version
        selected_pkgs = []
        for version in pkg_item['versions']:
            if version in cls.SPECIAL_VERSION_HANDLERS:
                res = cls.SPECIAL_VERSION_HANDLERS[version](rpm_pkg_list)
                if res is None:
                    cls.logger.warning("package {}'s special version tag {} does not select any item!".format(
                        pkg_item['name'], version))
                elif isinstance(res, list):
                    selected_pkgs.extend(res)
                else:
                    selected_pkgs.append(res)
                continue
            if version in rpm_pkg_map:
                selected_pkgs.append(rpm_pkg_map[version])
                continue
            raise ValueError("unknown version of package {}: {}".format(pkg_item['name'], version))

        if not selected_pkgs:
            raise ValueError("package {} does not select any item!".format(pkg_item['name']))
        cls.logger.info("selected {} packages are {}".format(
            pkg_item['name'], [pkg.version for pkg in selected_pkgs]))
        return selected_pkgs

    @classmethod
    def _parse_pkg_list(cls, pkg_list):
        pkg_item_list = []
        for pkg in pkg_list:
            if isinstance(pkg, str):
                pkg_item_list.append({'name': pkg})
            elif isinstance(pkg, dict):
                pkg_item_list.append(pkg)
            elif isinstance(pkg, (list, tuple)):
                pkg_item_list.extend(cls._parse_pkg_list(pkg))
            else:
                raise ValueError("unknown type of value", pkg)
        return pkg_item_list

    @classmethod
    def _ensure_repo_source(cls):
        """Install repository related tools, add extra online yum repository."""
        raise NotImplementedError

    @classmethod
    def get_rpm_dependency(cls, pkg_list):
        """Get latest full dependency package list from yum by a package list."""
        pkg_item_list = cls._parse_pkg_list(pkg_list)
        cls._ensure_repo_source()
        return cls._get_rpm_dependency_version(pkg_item_list)
