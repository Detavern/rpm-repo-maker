# coding: utf-8

import os
import logging
import logging.config


# enums: prod, test, dev
ENV = 'prod'
NAME = 'deployer'

CONFIG_DIR = os.path.abspath(os.path.dirname(__file__))
PROJ_DIR = os.path.abspath(os.path.dirname(CONFIG_DIR))
HOME_DIR = os.path.abspath(os.path.expanduser('~'))


class TERMColors:
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


# logging config
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'console': {
            'format': '{}[%(asctime)s][%(levelname)s]{}<%(name)s>{}(%(filename)s)->(LINE:%(lineno)d){}\n%(message)s'.format(
                TERMColors.HEADER, TERMColors.END, TERMColors.YELLOW, TERMColors.END)
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'level': 'DEBUG',
            # 'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'deployer': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# set logger
logging.config.dictConfig(LOGGING_CONFIG)
ROOT_LOGGER = logging.getLogger(NAME)
ROOT_LOGGER.setLevel(logging.INFO)
if ENV == 'dev':
    ROOT_LOGGER.setLevel(logging.DEBUG)
