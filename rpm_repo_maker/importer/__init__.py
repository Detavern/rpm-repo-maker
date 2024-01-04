from .base import RPMRepoImporter
from .pm_yum import YumRepoImporter
from .pm_dnf import DnfRepoImporter
from .pm_dnf_kylin import DnfKylinRepoImporter
from .pm_zypper import ZypperSLESRepoImporter


IMPORTER = {
    'yum': YumRepoImporter,
    'dnf': DnfRepoImporter,
    'dnf-kylin': DnfKylinRepoImporter,
    'zypper-nir': ZypperSLESRepoImporter,
}
