from .pm_yum import YumPackageFinder, YumRepoExporter
from .pm_dnf import DnfPackageFinder, DnfRepoExporter
from .pm_dnf_kylin import DnfKylinPackageFinder


FINDER = {
    'yum': YumPackageFinder,
    'dnf': DnfPackageFinder,
    'dnf-kylin': DnfKylinPackageFinder,
}

EXPORTER = {
    'yum': YumRepoExporter,
    'dnf': DnfRepoExporter,
    'dnf-kylin': DnfRepoExporter,
}
