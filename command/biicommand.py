import argparse
from biicode.common.exception import BiiException, InvalidNameException
from biicode.common.model.brl.block_name import BlockName
from biicode.common.model.symbolic.block_version import (BlockVersion,
                                                         parse_block_version_expression)
from biicode.client.client_hive_manager import ClientHiveManager, init_hive
from biicode.common.model.brl.brl_user import BRLUser
from biicode.client.shell.origin_manager import detect_updated_origin
from biicode.common.model.origin_info import OriginInfo
import re
from biicode.client.dev.cpp.cpptoolchain import CPPToolChain
from biicode.common.output_stream import Color


class BiiCommand(object):
    """ Global bii commands."""
    group = 'bii'

    def __init__(self, bii):
        self.bii = bii

    def buzz(self, *parameters):
        """ initialize project, find deps and builds in a single command """
        from biicode.client.exception import NotInAHiveException
        parser = argparse.ArgumentParser(description=BiiCommand.buzz.__doc__, prog="bii buzz")
        parser.add_argument('-G', metavar='"CMake generator"',
                            help='Define cmake generator. Type cmake --help to see'
                            ' available generators')
        args = parser.parse_args(*parameters)

        # BII INIT -L
        try:
            self.bii.bii_paths.project_root
        except NotInAHiveException:
            self.bii.user_io.out.writeln("Creating biicode project (simple layout)\n"
                                         "$ bii init -l", Color.BRIGHT_MAGENTA)
            init_hive(self.bii, None, "simple")

        # BII FIND
        self.bii.user_io.out.writeln("Looking for dependencies\n"
                                     "$ bii find", Color.BRIGHT_MAGENTA)
        self.find()

        if args.G:
            self.bii.user_io.out.writeln('Configuring with generator\n'
                                         '$ bii cpp:configure -G "%s"' % args.G,
                                         Color.BRIGHT_MAGENTA)
            CPPToolChain(self.bii).configure(["-G", args.G])
        # BII CPP:BUILD
        self.bii.user_io.out.writeln("Building\n"
                                     "$ bii cpp:build", Color.BRIGHT_MAGENTA)
        CPPToolChain(self.bii).build()

    def init(self, *parameters):
        """ creates a new biicode project"""
        parser = argparse.ArgumentParser(description=BiiCommand.init.__doc__, prog="bii init")
        parser.add_argument("name", nargs='?', default=None,
                            help='Optional name of the folder. If specified, bii will '
                            'create a new folder and initialize a project inside, '
                            'otherwise, it will try to initialize in the current folder')
        parser.add_argument("-L", "-l", "--layout", nargs='?', default=argparse.SUPPRESS,
                            help='Optional layout. If no param is specified, it will use '
                            'the "minimal" one. Other available: CLion')

        args = parser.parse_args(*parameters)  # To enable -h
        if not hasattr(args, "layout"):
            layout = None
        else:
            layout = args.layout if args.layout else "simple"

        if args.name == ".":  # Git style
            args.name = None

        init_hive(self.bii, args.name, layout)

    def user(self, *parameters):
        """ shows or change your current biicode user """
        parser = argparse.ArgumentParser(description=BiiCommand.user.__doc__, prog="bii user")
        parser.add_argument("name", nargs='?', default=None,
                            help='Username you want to use. '
                                 'It should be already registered in http://www.biicode.com. '
                                 'If no name is provided it will show the current user.')
        parser.add_argument("-p", "--password",
                            help='User password')
        args = parser.parse_args(*parameters)  # To enable -h
        user, _ = self.bii.user_cache.localdb.get_login()
        if not args.name:
            anon = '(anonymous)' if not user else ''
            self.bii.user_io.out.info('Current user: %s %s' % (user, anon))
        else:
            new_user = BRLUser(args.name)
            new_user = None if new_user == 'none' else new_user
            anon = '(anonymous)' if not new_user else ''
            if args.password is not None:
                token = self.bii.biiapi.authenticate(new_user, args.password)
            else:
                token = None
            if new_user == user:
                self.bii.user_io.out.info('Current user already: %s %s' % (user, anon))
            else:
                self.bii.user_io.out.info('Change user from %s to %s %s' % (user, new_user, anon))
                # TOOD: This temporary implementation, just cleans the database. A more efficient
                # implementation might just swap
                self.bii.user_cache.localdb.clean()
            self.bii.user_cache.localdb.set_login((new_user, token))

    def new(self, *parameters):
        """ wizard to create new block folder and, optionally, a Hello World"""
        parser = argparse.ArgumentParser(description=BiiCommand.init.__doc__, prog="bii new")
        parser.add_argument("block_name", default=False, nargs='?',
                            help='Block Name USER_NAME/BLOCK_NAME, '
                            'e.g.: my_user/my_block',
                            type=block_name)

        parser.add_argument("--hello", default=None, type=str, nargs=1,
                            help='Creates a "Hello World" main. You need to specify the language '
                            'in which the main file will be created, e.g.: --hello cpp')
        args = parser.parse_args(*parameters)  # To enable -h
        if not (args.block_name or args.hello):
            parser.error('No action requested, add block_name or --hello')
        manager = ClientHiveManager(self.bii)
        manager.new(args.block_name, args.hello)

    def clean(self, *parameters):
        """ cleans project database, temporal and build files """
        parser = argparse.ArgumentParser(description=BiiCommand.clean.__doc__,
                                         prog="bii clean")
        parser.add_argument("--cache", default=False,
                            action='store_true',
                            help='Delete user cache.')

        args = parser.parse_args(*parameters)
        client_hive_manager = ClientHiveManager(self.bii)
        client_hive_manager.clean()
        if args.cache:
            self.bii.user_cache.localdb.clean()

    def diff(self, *parameters):
        ''' compare files and show differences.
        You can compare your current project with previous published versions or compare between
        published versions.
        '''
        parser = argparse.ArgumentParser(description=BiiCommand.diff.__doc__, prog="bii diff")
        parser.add_argument("block_name", help='Block Name USER_NAME/BLOCK_NAME, '
                                               'e.g.: my_user/my_block',
                            type=block_name, nargs='?')
        parser.add_argument("v1", help='Child block version',
                            type=int, default=None, nargs='?')
        parser.add_argument("v2", help='Parent block version',
                            type=int, default=None, nargs='?')
        parser.add_argument("--short", default=False,
                            action='store_true',
                            help='View the basic information about your block/s status')
        # TODO: Remote option is not possible while sync manager is out of service
        args = parser.parse_args(*parameters)  # To enable -h
        manager = ClientHiveManager(self.bii)
        manager.diff(args.block_name, args.v1, args.v2, args.short)

    def close(self, *parameters):
        """ close a block under edition.
        If it's a dependency, moves it to dependencies folder
        """
        parser = argparse.ArgumentParser(description=self.close.__doc__, prog="bii close")
        parser.add_argument("block", type=block_name,
                            help='Block to close USER_NAME/BLOCK_NAME, '
                                 'e.g.: my_user/my_block')
        parser.add_argument("--force", default=False,
                            action='store_true',
                            help='Closes the block even if it has unpublished changes')

        args = parser.parse_args(*parameters)  # To enable -h
        manager = ClientHiveManager(self.bii)
        manager.close(args.block, args.force)

    def open(self, *parameters):
        ''' it allows you to edit any existing block'''
        parser = argparse.ArgumentParser(description=BiiCommand.open.__doc__, prog="bii open")
        help_msg = ('Block name. eg: bii open my_user/my_block, '
                    'or block version. E.g: bii open "my_user/my_block(user/branch): 7"')
        parser.add_argument("block", help=help_msg)
        args = parser.parse_args(*parameters)  # To enable -h
        try:
            brl_block, time, version_tag = parse_block_version_expression(args.block)
        except:
            raise BiiException("Bad parameter: %s" % help_msg)
        # user has specified track or not
        track = brl_block.owner_branch if '(' in args.block else None
        manager = ClientHiveManager(self.bii)
        manager.open(brl_block.block_name, track, time, version_tag)

    def deps(self, *parameters):
        """ show information about current project dependencies.
        """
        args = _BiiArgParser.get_deps_params(*parameters)
        manager = ClientHiveManager(self.bii)
        manager.deps(args.block_name, args.details, args.files)

    def work(self, *parameters):
        ''' ADVANCED Save and process pending changes.'''
        parser = argparse.ArgumentParser(description=self.work.__doc__,
                                         prog="bii work")
        parser.parse_args(*parameters)  # To enable -h
        client_hive_manager = ClientHiveManager(self.bii)
        client_hive_manager.work()
        self.bii.user_io.out.write('Work done!\n')

    def build(self, *parameters):
        """ alias for cpp:build
        """
        CPPToolChain(self.bii).build(*parameters)

    def configure(self, *parameters):
        """ alias for cpp:configure
        """
        CPPToolChain(self.bii).configure(*parameters)

    def test(self, *parameters):
        """ alias for cpp:test
        """
        CPPToolChain(self.bii).test(*parameters)

    def find(self, *parameters):
        ''' looks in server for unresolved dependencies'''
        find_args = _BiiArgParser.get_find_params(*parameters)
        find_args = vars(find_args)
        manager = ClientHiveManager(self.bii)
        manager.find(**find_args)

    def publish(self, *parameters):
        ''' publish one or all the blocks of the current project'''
        publish_args = _BiiArgParser.get_publish_params(*parameters)
        block_name, tag, versiontag, msg, publish_all, origin = publish_args
        if block_name and publish_all:
            raise BiiException('Do not specify block name with --all option')
        if publish_all and origin:
            raise BiiException('Do not specify --all with --remote option')

        if origin and origin.url is None:  # Entered empty -r option
            origin = self._auto_detect_origin_info(origin, block_name)

        hive_manager = ClientHiveManager(self.bii)
        hive_manager.publish(block_name, tag, msg, versiontag, publish_all, origin)

    def update(self, *parameters):
        ''' EXPERIMENTAL update an outdated block
        If one of your block is outdated, because you have published from another project or
        computer, you cannot publish again.
        If you want to discard your current changes, just close-open the block.
        If you have made changes in your block that you dont want to lose, and you want also the
        last changes in the server, you can use this command.
        If you want just to override the last published version, you can always point your
        parents.bii to the last published version.
        '''
        block, time = _BiiArgParser.get_update_params(*parameters)
        manager = ClientHiveManager(self.bii)
        manager.update(block, time)

    def _auto_detect_origin_info(self, origin, block_name):
        hive_disk_image = self.bii.hive_disk_image
        hive_disk_image.update_root_block()
        disk_blocks = hive_disk_image.disk_blocks
        if block_name is None and len(disk_blocks) > 1:
            raise BiiException('Current project blocks:\n\t'
                               '\n\t'.join(disk_blocks) + 'Please specify block to publish'
                               ' with "$ bii publish my_user/my_block"')

        try:
            block_name = block_name or disk_blocks.keys()[0]
            block_path = disk_blocks[block_name]
        except:
            raise BiiException("No block %s to publish in this project" % (block_name or ""))

        try:
            origin = detect_updated_origin(block_path)
            self.bii.user_io.out.info("Detected origin: %s" % str(origin))
        except BiiException as exc:  # Not auto detected, request input
            self.bii.user_io.out.warn(str(exc))
            self.bii.user_io.out.info("Input origin info:")
            url = self.bii.user_io.request_string("Url", origin.url)
            branch = self.bii.user_io.request_string("Branch", origin.branch)
            commit = self.bii.user_io.request_string("Tag", origin.tag)
            origin_tag = self.bii.user_io.request_string("Commit", origin.commit)
            origin = OriginInfo(url, branch, commit, origin_tag)

        return origin


class _BiiArgParser(object):
    @staticmethod
    def get_update_params(*parameters):
        parser = argparse.ArgumentParser(description=BiiCommand.update.__doc__, prog="bii update")
        parser.add_argument("block", nargs='?', default=None,
                            help='Block name, e.g.: bii update my_user/my_block. ',
                            type=block_name)
        parser.add_argument("--time",
                            help='Time to update. Default=last', type=int)
        args = parser.parse_args(*parameters)
        return args.block, args.time

    @staticmethod
    def get_publish_params(*parameters):
        def version_tag(value):
            '''function to avoid argparse error message override'''
            from biicode.common.model.version_tag import VersionTag
            try:
                return VersionTag.loads(value)
            except ValueError as e:
                raise BiiException(str(e))

        parser = argparse.ArgumentParser(description=BiiCommand.publish.__doc__,
                                         prog="bii publish")
        parser.add_argument("block", nargs='?', default=None,
                            help='Block name, e.g.: bii publish my_user/my_block. '
                            'Do not use with --all argument', type=block_name)
        parser.add_argument("--tag",
                            help='Release life-cycle TAG, e.g: bii publish --tag ALPHA',
                            type=version_tag)
        parser.add_argument("--versiontag",
                            help='Name tag for the version. e.g: v1.2 or "Sweet Beacon" ',
                            type=str)
        parser.add_argument("--msg", help='DEPRECATED: Publication description')
        parser.add_argument("--all", default=False, action='store_true',
                            help='Publish all blocks. Do not use with block argument')
        parser.add_argument("-r", "--remote", default=argparse.SUPPRESS, type=str, nargs="?",
                            help='Publish VCS remote info. Format:'
                                 ' "remote_url (branch) @commit_id #tag" or blank to autodetect '
                                 '(currently only git supported)')

        args = parser.parse_args(*parameters)

        if 'remote' in args:
            if args.remote:
                reg = "^(?P<url>\S*)(\s\((?P<branch>\S*)\))*" \
                      "(\s@(?P<commit>\S*))*(\s#(?P<tag>\S*))*\s*$"
                pattern = re.compile(reg)
                values = [m.groupdict() for m in pattern.finditer(args.remote)]
                if len(values) == 0:  # Not Match
                    raise BiiException("Origin info is not valid!")

                values = values[0]
                origin = OriginInfo(values.get("url", None),
                                    values.get("branch", None),
                                    values.get("tag", None),
                                    values.get("commit", None),
                                    )

            else:  # Force autodetect
                origin = OriginInfo(None, None, None, None)
        else:
            origin = None

        return args.block, args.tag, args.versiontag, args.msg, args.all, origin

    @staticmethod
    def get_deps_params(*parameters):
        parser = argparse.ArgumentParser(description=BiiCommand.deps.__doc__, prog="bii deps")
        parser.add_argument("block_name", nargs='?', default=None,
                            help='Block name. E.g.: my_user/my_block',
                            type=block_name)
        parser.add_argument("--details", type=str, nargs='*',
                            help='Show a list with dependencies for each file')
        parser.add_argument("--files", type=str, nargs='*',
                            help='Show dependencies of given list of files')

        # graph show options:
        # FIXME: Temporary disabled, broken web templates.
        # parser.add_argument("--graph", default=False, action='store_true',
        #                    help='Show a graph with all projects blocks dependencies')
        args = parser.parse_args(*parameters)  # To enable -h
        return args

    @staticmethod
    def get_find_params(*parameters):
        parser = argparse.ArgumentParser(description=BiiCommand.find.__doc__,
                                         prog="bii find")
        parser.add_argument("-f", "--find", default=True, action='store_true',
                            help='Search unresolved dependencies. Default=true')
        parser.add_argument("-u", "--update", default=False, action='store_true',
                            help='Allow updating existing dependencies. Default=false')
        parser.add_argument('-d', "--downgrade", default=False, action='store_true',
                            help='Allow downgrading existing dependencies. Default=false')
        parser.add_argument('-m', "--modify", default=False, action='store_true',
                            help='Allow changing dependencies due your policies. Default=false'
                            ' as in a new find invocation')
        args = parser.parse_args(*parameters)
        return args


def block_version(argument):
    return argument if isinstance(argument, BlockVersion) else BlockVersion.loads(argument)


def block_name(argument):
    try:
        return BlockName(argument)
    except InvalidNameException as e:
        raise BiiException('%s, e.g.: my_user/my_block' % e.message)
