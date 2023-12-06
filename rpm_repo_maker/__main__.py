# coding: utf-8

import os
import sys
import json
import argparse

from .exporter import FINDER, EXPORTER
from .importer import IMPORTER
from .helper import cmd_exists

NO_SUB_CMD_MSG = 'command required'


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('arguments parse error: {}\n'.format(message))
        if message == NO_SUB_CMD_MSG:
            self.print_help()
        # for python2.7
        if message == 'too few arguments':
            self.print_help()
        sys.exit(2)


def read_manager(parser, args):
    # which package manager
    if args.pkg_mgr:
        return

    if cmd_exists('dnf'):
        args.pkg_mgr = 'dnf'
    elif cmd_exists('yum'):
        args.pkg_mgr = 'yum'
    else:
        parser.error('need specify "-m" option')


def read_config(parser, args):
    # config str or file
    if args.config_str:
        try:
            cfg = json.loads(args.config_str)
        except json.JSONDecodeError as e:
            parser.error("read config error: {}".format(e))
        else:
            return cfg[args.pkg_mgr]
    if args.config_file:
        try:
            cfg = json.load(args.config_file)
        except json.JSONDecodeError as e:
            parser.error("read config error: {}".format(e))
        else:
            return cfg[args.pkg_mgr]


def print_config(parser, args):
    read_manager(parser, args)
    cfg = read_config(parser, args)
    print("Package manager is {}".format(args.pkg_mgr))
    print(cfg)


def generate_offline_bundle(parser, args):
    read_manager(parser, args)
    cfg = read_config(parser, args)
    # resolve dependency
    finder = FINDER[args.pkg_mgr]
    pkgs = finder.get_rpm_dependency(cfg)
    print(pkgs)

    # make repo
    exporter_cls = EXPORTER[args.pkg_mgr]
    exporter = exporter_cls(
        args.repository,
        os.path.expanduser('~'),
        platform_suffix=args.suffix,
    )
    exporter(pkgs)


def import_offline_bundle(parser, args):
    read_manager(parser, args)
    # import repo
    importer_cls = IMPORTER[args.pkg_mgr]
    importer = importer_cls(
        args.repository,
        args.repo_file,
    )
    importer(args.repo_path)


def main():
    # root parser
    parser = MyParser(
        prog="rpm-repo-maker",
        description="RPM repository maker",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sp = parser.add_subparsers(help='sub-command help')

    # command print
    cmd_print = sp.add_parser('print', help='Print for debug.')
    cmd_print.set_defaults(func=print_config)
    cmd_print.add_argument('-m', '--manager', dest='pkg_mgr', type=str, help='specify package manager')
    group_cfg = cmd_print.add_mutually_exclusive_group(required=True)
    group_cfg.add_argument('-s', '--string', dest='config_str', type=str, default='',
                           help='configuration string')
    group_cfg.add_argument('-c', '--config', dest='config_file', type=argparse.FileType('r'),
                           help='configuration file path')

    # command generate
    cmd_gen = sp.add_parser('generate', help='Generate offline repository bundle.')
    cmd_gen.set_defaults(func=generate_offline_bundle)
    cmd_gen.add_argument('repository', type=str, help='generated repository name')
    cmd_gen.add_argument('-u', '--suffix', dest='suffix', type=str, help='use customized suffix')
    cmd_gen.add_argument('-m', '--manager', dest='pkg_mgr', type=str, help='specify package manager')
    group_cfg = cmd_gen.add_mutually_exclusive_group(required=True)
    group_cfg.add_argument('-s', '--string', dest='config_str', type=str, default='',
                           help='configuration string')
    group_cfg.add_argument('-c', '--config', dest='config_file', type=argparse.FileType('r'),
                           help='configuration file path')

    # command import
    cmd_import = sp.add_parser('import', help='Import offline repository bundle.')
    cmd_import.set_defaults(func=import_offline_bundle)
    cmd_import.add_argument('repository', type=str, help='import repository name')
    cmd_import.add_argument('-m', '--manager', dest='pkg_mgr', type=str, help='specify package manager')
    cmd_import.add_argument('-f', '--file', dest='repo_file', type=str, default='',
                            help='repository bundle to import')
    cmd_import.add_argument('-p', '--path', dest='repo_path', type=str, default='/opt/rpm',
                            help='local repository path')

    # args
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(parser, args)
    else:
        # no cmd fallback
        raise parser.error(NO_SUB_CMD_MSG)


if __name__ == '__main__':
    main()
