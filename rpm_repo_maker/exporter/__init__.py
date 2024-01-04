from .pm_yum import YumPackageFinder, YumRepoExporter
from .pm_dnf import DnfPackageFinder, DnfRepoExporter
from .pm_dnf_kylin import DnfKylinPackageFinder
from .pm_zypper_nir import ZypperNIRPackageFinder, ZypperNIRRepoExporter


FINDER = {
    'yum': YumPackageFinder,
    'dnf': DnfPackageFinder,
    'dnf-kylin': DnfKylinPackageFinder,
    'zypper-nir': ZypperNIRPackageFinder,
}

EXPORTER = {
    'yum': YumRepoExporter,
    'dnf': DnfRepoExporter,
    'dnf-kylin': DnfRepoExporter,
    'zypper-nir': ZypperNIRRepoExporter,
}
