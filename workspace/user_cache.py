import os
from biicode.common.utils.file_utils import save, load
from biicode.client.store.localdb import LocalDB
from biicode.common.find.policy import default_policies


_simple_layout = """ # Minimal layout, with all auxiliary folders inside "bii" and
# The binary "bin" folder as is, and enabled code edition in the project root
cmake: bii/cmake
lib: bii/lib
build: bii/build\n
deps: bii/deps
# Setting this to True enables directly editing in the project root
# instead of blocks/youruser/yourblock
# the block will be named as your project folder
auto-root-block: True
"""

_clion_layout = """ # Layout for CLion IDE with root CMakeLists at project root
# This layout DOES NOT allow root-block, as it will overwrite the project CMakeLists
cmake: /
"""

_tmp_layout = """ # Layout that redirect aux folders to your tmp/project folder
cmake: $TMP/cmake
lib: $TMP/lib
build: $TMP/build
deps: $TMP/deps
auto-root-block: True
"""


class UserCache(object):

    def __init__(self, folder):
        """Path to folder to write files"""
        self._folder = folder
        self._username = None
        self._localdb = None

    @property
    def folder(self):
        return self._folder

    def _create_layout_templates(self):
        for name, content in {"simple": _simple_layout,
                              "clion": _clion_layout,
                              "tmp": _tmp_layout}.iteritems():
            layout_path = os.path.join(self._folder, "%s_layout.bii" % name)
            if not os.path.exists(layout_path):
                save(layout_path, content)

    def layout(self, name):
        if not name:
            return None
        self._create_layout_templates()
        layout_path = os.path.join(self._folder, name.lower() + "_layout.bii")
        if os.path.exists(layout_path):
            return load(layout_path)

    @property
    def bii_ignore(self):
        from biicode.client.workspace.bii_ignore import BiiIgnore, default_bii_ignore
        path = os.path.join(self._folder, 'ignore.bii')
        if not os.path.exists(path):
            save(path, default_bii_ignore)
        return BiiIgnore.loads(load(path))

    @property
    def localdb(self):
        '''return instance of LocalDB'''
        if self._localdb is None:
            path = os.path.join(self._folder, 'bii.db')
            self._localdb = LocalDB(path)
        return self._localdb

    @property
    def username(self):
        if self._username is None:
            self._username = self.localdb.get_username()
        return self._username

    @property
    def default_policies(self):
        """ Return default WS policies.

        @return: default workspace policies
        """
        path = os.path.join(self._folder, 'default_policies.bii')
        if not os.path.exists(path):
            # load hardcoded default policies: default_policies
            save(path, default_policies)
            return default_policies
        current_defaults = load(path)
        # Migration to new simple policies.bii format
        if current_defaults.lstrip().startswith("# This is the file"):
            current_defaults = default_policies
            save(path, default_policies)
        return current_defaults

    def close(self):
        if self._localdb is not None:
            self._localdb.disconnect()
            self._localdb = None
