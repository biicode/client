import os
import shutil
from biicode.client.exception import ClientException
from biicode.common.utils import file_utils
from biicode.common.find.policy import Policy
from biicode.client.store import hivedb
from biicode.common.utils.file_utils import save, load
from biicode.common.settings.settings import Settings
from biicode.client.workspace.bii_paths import (BiiPaths, DEP_DIR, BIN_DIR, BUILD_DIR, CMAKE_DIR,
                                                LIB_DIR, BII_DIR, SRC_DIR)
from biicode.client.workspace.walk_block import walk_bii_folder, walk_anonymous_block
import fnmatch
from biicode.common.model.brl.block_name import BlockName
from biicode.common.edition.bii_config import BiiConfig
from biicode.common.model.blob import Blob


class HiveDiskImage(object):
    """Handle all actions related to hive in disk."""

    def __init__(self, bii_paths, user_cache, biiout):
        assert isinstance(bii_paths, BiiPaths)
        self._bii_paths = bii_paths
        self._user_cache = user_cache
        self._biiout = biiout
        self._hivedb = None
        self._settings = None
        self._policies = None

    @property
    def paths(self):
        return self._bii_paths

    def initialize(self):
        self._hivedb = hivedb.factory(self._bii_paths.new_project_db)
        self.settings
        self.policies

    def clean(self):
        try:
            self.hivedb.clean()
        except Exception as e:
            self._biiout.error("Unable to properly clean project DB:\n%s" % str(e))

        protect = {os.path.normpath(self._bii_paths.get_by_name(p)): p for p in (BII_DIR, SRC_DIR)}
        protect[self._bii_paths.project_root] = "project root"
        for folder in [BUILD_DIR, BIN_DIR, CMAKE_DIR, DEP_DIR, LIB_DIR]:
            try:
                path_folder = os.path.normpath(self._bii_paths.get_by_name(folder))
                if os.path.exists(path_folder):
                    if path_folder in protect:
                        self._biiout.warn("%s folder will not be cleaned" % folder)
                        self._biiout.warn("It matches the '%s' folder" % protect[path_folder])
                    else:
                        shutil.rmtree(path_folder)
            except Exception as e:
                self._biiout.error("Unable to delete %s folder\n%s" % (folder, str(e)))

    @property
    def settings(self):
        """ Return Hive settings.
        If settings.bii not present, creates and initialize a default hive settings.bii
        """
        if self._settings is None:
            settings_path = self._bii_paths.settings
            if not os.path.exists(settings_path):        # CREATE new hive settings file
                settings = Settings()           # empty settings, only OS information
                save(settings_path, settings.dumps())    # save settings.bii
                self._settings = settings
            else:                               # LOAD existing settings.bii file
                try:
                    self._settings = Settings.loads(load(settings_path))
                except Exception as e:
                    raise ClientException('%s\nIn file %s'
                                          % (str(e), settings_path.replace('\\', '/')))
        return self._settings

    @settings.setter
    def settings(self, value):
        """Set hive settings and save.

        :param value: new hive settings
        :type value: biicode.common.settings.settings.Settings

        """
        self._settings = value
        save(self._bii_paths.settings, value.dumps())

    @property
    def policies(self):
        if self._policies is None:
            policies_path = self._bii_paths.policies
            if not os.path.exists(policies_path):
                policies = self._user_cache.default_policies
                save(policies_path, policies)
            else:
                policies = load(policies_path)
                # Migration to new simple policies.bii format
                if policies.lstrip().startswith("# This is the file"):
                    self._biiout.warn("Upgrading your find policies to new format")
                    policies = self._user_cache.default_policies
                    save(policies_path, policies)
            if "YOUR_USER_NAME" in policies:
                user = self._user_cache.username
                if user is not None:
                    policies = policies.replace("YOUR_USER_NAME", user)
                    save(policies_path, policies)
            self._policies = Policy.loads(policies)
        return self._policies

    def create_new_block(self, block_name):
        ''' Creates block folders and main files if the language is specified'''
        assert block_name
        user, block = block_name.split('/')  # Windows uses backslashes
        # Create the block folder
        new_block_path = os.path.join(self._bii_paths.blocks, user, block)
        if not os.path.exists(new_block_path):
            os.makedirs(new_block_path)
            msg_succes = "Success: created {block_name} folder in your blocks directory!"
            self._biiout.success(msg_succes.format(block_name=block_name))
        else:
            msg_info = "{block_name} folder already exists in your blocks directory"
            self._biiout.info(msg_info.format(block_name=block_name))
        return new_block_path

    def create_new_file(self, block_path, file_name, content=''):
        ''' Create main files with Hello World templates '''
        file_path = os.path.join(block_path, file_name)
        save(file_path, content)  # save method handles exceptions
        msg_succes = 'Success: created {file_name} file in {path}'
        self._biiout.success(msg_succes.format(file_name=file_name, path=block_path))

    def delete_build_folder(self):
        if os.path.exists(self._bii_paths.build):
            shutil.rmtree(self._bii_paths.build)
            os.makedirs(self._bii_paths.build)

    @property
    def hivedb(self):
        """Return HiveDB object."""
        if self._hivedb is None:
            self._hivedb = hivedb.factory(self._bii_paths.hivedb)
        return self._hivedb

    def close(self):
        if self._hivedb is not None:
            self._hivedb.disconnect()
            self._hivedb = None

    def update_root_block(self):
        if self._bii_paths.auto_root_block:
            bii_config_path = os.path.join(self._bii_paths.project_root, "biicode.conf")
            parent = (None if not os.path.exists(bii_config_path) else
                      BiiConfig(Blob(load(bii_config_path)).bytes).parent)
            if parent:
                project_block = parent.block_name
            else:  # Get the root block name from user + folder
                project_name = self._bii_paths.project_name
                user = self._user_cache.username or "user"
                project_block = BlockName("%s/%s" % (user, project_name))
            self._bii_paths.root_block = project_block

    def get_src_files(self):
        """ scans the SRC_DIR to obtain a {BlockCellName: ByteLoad}
        """
        #scan regular block folder
        bii_ignore = self._user_cache.bii_ignore
        result = walk_bii_folder(self._bii_paths.blocks, bii_ignore, self._biiout)

        # check if the project root has to be scanned
        self.update_root_block()
        project_block = self._bii_paths.root_block

        # scan project root
        if project_block:
            result_filter = {bcn: content for bcn, content in result.iteritems()
                             if bcn.block_name != project_block}
            if len(result) != len(result_filter):
                self._biiout.warn("Skipping %s block, it already exist in project root"
                                  % project_block)
            result = result_filter
            anon = walk_anonymous_block(self._bii_paths, bii_ignore, self._biiout, project_block)
            result.update(anon)
        return result

    def clean_hooks(self):
        for folder in (self._bii_paths.blocks, self._bii_paths.deps):
            for _, _, files in os.walk(folder):
                for f in files:
                    if fnmatch.fnmatch(f, "bii*clean*hook*"):
                        return True
        return False

    @property
    def disk_blocks(self):
        """Get the blocks based on disk, not in processed hive"""
        result = {}
        root_block = self._bii_paths.root_block
        if os.path.exists(self._bii_paths.blocks):
            for username in os.listdir(self._bii_paths.blocks):
                for name in os.listdir(os.path.join(self._bii_paths.blocks, username)):
                    tmp_path = os.path.join(self._bii_paths.blocks, username, name)
                    if(os.path.isdir(tmp_path)):
                        block_name = BlockName("%s/%s" % (username, name))
                        if root_block == block_name:
                            self._biiout.warn("Skipping %s, it exists as root block" % root_block)
                        elif(os.listdir(tmp_path)):  # If there is any file inside
                            result[block_name] = os.path.join(self._bii_paths.blocks, block_name)
        if root_block:
            result[root_block] = self._bii_paths.project_root
        return result

    def save(self, folder_name, files):
        saved_blocks = set()
        project_block = self._bii_paths.root_block
        folder = self._bii_paths.get_src_folder(folder_name)
        for disk_bcn, load in files.iteritems():
            if disk_bcn.block_name == project_block:
                filepath = os.path.join(self._bii_paths.project_root, disk_bcn.cell_name)
            else:
                filepath = os.path.join(folder, disk_bcn)
            try:
                file_content = file_utils.load(filepath)
            except:
                file_content = None
            if file_content != load:
                if folder_name == DEP_DIR and disk_bcn.block_name not in saved_blocks:
                    saved_blocks.add(disk_bcn.block_name)
                    self._biiout.info("Saving files from: %s" % disk_bcn.block_name)
                file_utils.save(filepath, load)

    def delete_removed(self, folder_name, current_block_cell_names, block_filter=None):
        """ current_block_cell_names is the set of BlockCellNames currently in closure
        Items not in closure, can be deleted
        Params:
            folder_name = SRC_DIR or DEP_DIR
            current_block_cell_names = [BlockCellName]
            block_filter = BlockName or None
                         if BlockName only files from that BlockName will be deleted
        """
        bii_ignore = self._user_cache.bii_ignore
        folder = self._bii_paths.get_src_folder(folder_name)
        root_block = self._bii_paths.root_block
        project_folder = self._bii_paths.project_root
        # Files on biicode control (excluded ignored)
        thefiles = walk_bii_folder(folder, bii_ignore, self._biiout)
        if root_block and folder_name == SRC_DIR:
            afiles = walk_anonymous_block(self._bii_paths, bii_ignore, self._biiout, root_block)
            thefiles.update(afiles)

        # Delete removed cells
        for blockcellname in thefiles:
            if ((not block_filter or blockcellname.block_name == block_filter) and
                blockcellname not in current_block_cell_names):
                if blockcellname.block_name == root_block:
                    filepath = os.path.join(project_folder, blockcellname.cell_name)
                else:
                    filepath = os.path.join(folder, blockcellname)
                os.unlink(filepath)

        self._delete_empty_dirs(folder_name, block_filter)

    def _delete_empty_dirs(self, folder_name, block_name=None):
        folder = self._bii_paths.get_src_folder(folder_name)
        if block_name is not None:
            folder = os.path.join(folder, block_name)

        for root, _, _ in os.walk(folder, topdown=False):
            try:
                os.rmdir(root)
            except OSError:
                pass  # not empty

        if block_name:
            try:
                os.rmdir(os.path.dirname(folder))
            except OSError:
                pass  # not empty
