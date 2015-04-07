""" Handles ALL paths involved in the execution of a bii command
"""
import os
from biicode.client.exception import NotInAHiveException
from biicode.common.settings.osinfo import OSInfo
from biicode.common.edition.parsing.conf.conf_file_parser import parse
from biicode.common.exception import ConfigurationFileError
from biicode.common.utils.file_utils import load, save
from biicode.common.model.brl.block_name import BlockName
import tempfile


# These are the standard internal names, to refer in code, DO NOT change
SRC_DIR = 'blocks'
DEP_DIR = 'deps'
BUILD_DIR = 'build'
BIN_DIR = 'bin'
BII_DIR = 'bii'
CMAKE_DIR = 'cmake'
BII_HIVE_DB = '.hive.db'
USER_BII_HOME = '.biicode'
LIB_DIR = "lib"
AUTO_ROOT_BLOCK = "auto-root-block"
ROOT_BLOCK = "root-block"


default_layout = {SRC_DIR: SRC_DIR,
                  DEP_DIR: DEP_DIR,
                  BUILD_DIR: BUILD_DIR,
                  BIN_DIR: BIN_DIR,
                  CMAKE_DIR: CMAKE_DIR,
                  LIB_DIR: LIB_DIR,
                  AUTO_ROOT_BLOCK: False,
                  ROOT_BLOCK: None}


def parse_layout_conf(text, project_root):
    """ parses a layout.bii file, with the format:
    lib: mylib
    deps: dependencies
    ...
    """
    current_layout = default_layout.copy()

    def parse_dependencies(line):
        tokens = line.strip().split(':', 1)
        if len(tokens) != 2:
            raise ConfigurationFileError('Every entry in layout should be NAME: RELATIVE PATH')
        name, value = tokens
        if name not in default_layout:
            raise ConfigurationFileError('Unknown layout entry %s' % name)
        # relative path between tmp and project with the project name as dest folder
        if "$TMP" in value:
            try:
                tmp_rel_folder = os.path.join(os.path.relpath(tempfile.gettempdir(), project_root),
                                              os.path.basename(project_root)).replace('\\', '/')
            except Exception:
                raise ConfigurationFileError("Unable to compute relative path to $TMP folder "
                                             "in layout.bii\nYou are probably in another drive "
                                             "to your tmp folder")
            value = value.replace("$TMP", tmp_rel_folder)
        value = value.strip()
        if value == "/" or value.lower() == "false":
            value = ""
        if name == ROOT_BLOCK:
            value = BlockName(value)
        current_layout[name] = value

    parse(text,  parse_dependencies)
    # Lets make sure nothing else is inside the edited blocks folder
    src_dir = current_layout[SRC_DIR]
    for name, path in current_layout.iteritems():
        if name not in [SRC_DIR, AUTO_ROOT_BLOCK, ROOT_BLOCK] and path.startswith(src_dir):
            raise ConfigurationFileError('Layout: Please do not locate %s inside blocks' % name)
    return current_layout


def get_biicode_env_folder_path():
    """ this folder is used to store automatically downloaed ArduinoSDK and RPI cross compilers
    """
    if OSInfo.is_win():
        return os.path.normpath("C:/biicode_env")
    else:
        return os.path.expanduser("~/.biicode_env")


class BiiPaths(object):
    """ Contains all the path references for a biicode running instance
    """
    def __init__(self, current_dir, user_home):
        """ current_dir: The getcwd() of execution
        user_home: the place where the local.db cache and all the user stuff lives,
                   if None, it will be computed as os.path.expanduser("~")
        """
        assert user_home
        assert current_dir
        self._project_root = None  # lazy computed and cached
        self._current_layout = None  # lazy loaded from file and cached
        self._current_dir = current_dir  # The dir user runs the command from
        self._user_home = user_home

    @property
    def current_dir(self):
        return self._current_dir

    @current_dir.setter
    def current_dir(self, value):
        self._project_root = None
        self._current_dir = value

    @property
    def user_bii_home(self):
        """ user biicode home is .biicode, is independent of project
        location
        """
        # FIXME: Dirty hack to the problem of different origins for self._user_home
        # Should be fixed in last commit, but to be checked
        if os.path.basename(self._user_home) == USER_BII_HOME:
            return self._user_home
        return os.path.join(self._user_home, USER_BII_HOME)

    @property
    def cmake_path_file(self):
        """ path of the file that define the cmake executable location
        """
        return os.path.join(self.user_bii_home, 'cmake_path')

    @property
    def project_root(self):
        """ searchs for bii folder with project database inside
        actually requires the folder to be named -bii-
        """
        if self._project_root is None:
            self._project_root = BiiPaths._find_project_root(self._current_dir)
        return self._project_root

    @property
    def project_name(self):
        """ the individual name of the project folder
        """
        return os.path.basename(self.project_root)

    @property
    def bii(self):
        """ The -bii- folder of the project
        """
        return os.path.join(self.project_root, BII_DIR)

    @property
    def settings(self):
        """ Path to the settings.bii file
        """
        return os.path.join(self.bii, 'settings.bii')

    @property
    def policies(self):
        """ Find policies path.
        """
        return os.path.join(self.bii, 'policies.bii')

    @property
    def hivedb(self):
        return os.path.join(self.bii, BII_HIVE_DB)

    @property
    def new_project_db(self):
        return os.path.join(self._current_dir, BII_DIR, BII_HIVE_DB)

    @property
    def _layout(self):
        if self._current_layout is None:
            layout_path = os.path.join(self.bii, "layout.bii")
            if os.path.exists(layout_path):
                self._current_layout = parse_layout_conf(load(layout_path),
                                                         self.project_root)
            else:
                self._current_layout = default_layout
        return self._current_layout

    def get_by_name(self, folder_name):
        return getattr(self, folder_name)

    def get_src_folder(self, folder_name):
        if folder_name == SRC_DIR:
            return self.blocks
        elif folder_name == DEP_DIR:
            return self.deps
        raise ValueError('Bad folder %s' % folder_name)

    @property
    def root_block(self):
        return self._layout[ROOT_BLOCK]

    @root_block.setter
    def root_block(self, value):
        assert isinstance(value, BlockName)
        self._current_layout[ROOT_BLOCK] = value
        layout_path = os.path.join(self.bii, "layout.bii")
        layout = load(layout_path)
        new_layout = []
        for line in layout.splitlines():
            if ROOT_BLOCK not in line or AUTO_ROOT_BLOCK in line:
                new_layout.append(line)
        new_layout.append("%s: %s" % (ROOT_BLOCK, value))
        new_layout = os.linesep.join(new_layout)
        save(layout_path, new_layout)

    @property
    def auto_root_block(self):
        return self._layout[AUTO_ROOT_BLOCK]

    @property
    def blocks(self):
        """ folder where the opened/edition code lives
        """
        _path = self._layout[SRC_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def blocks_relative(self):
        """ the relative path of the blocks folder wrt project root
        """
        return self._layout[SRC_DIR]

    @property
    def cmake(self):
        _path = self._layout[CMAKE_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def cmake_relative(self):
        return self._layout[CMAKE_DIR]

    @property
    def build(self):
        _path = self._layout[BUILD_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def bin(self):
        _path = self._layout[BIN_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def bin_relative(self):
        return self._layout[BIN_DIR]

    @property
    def deps(self):
        _path = self._layout[DEP_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def deps_relative(self):
        return self._layout[DEP_DIR]

    @property
    def lib(self):
        _path = self._layout[LIB_DIR]
        return os.path.normpath(os.path.join(self.project_root, _path))

    @property
    def lib_relative(self):
        return self._layout[LIB_DIR]

    @staticmethod
    def _find_project_root(current_dir):
        """ recursive method to find the root folder of a bii project
        """
        if current_dir is None or not os.path.exists(current_dir):
            raise NotInAHiveException()

        if os.path.exists(os.path.join(current_dir, BII_DIR, BII_HIVE_DB)):
            return current_dir
        parent = os.path.abspath(os.path.join(current_dir, os.pardir))
        if parent == current_dir:
            raise NotInAHiveException()
        try:
            return BiiPaths._find_project_root(parent)
        except Exception:
            raise NotInAHiveException()
