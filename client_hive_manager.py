from biicode.common.edition.hive_manager import HiveManager
from biicode.client.exception import ConnectionErrorException, ClientException, NotInAHiveException
from biicode.client.checkout.snapshotbuilder import compute_files, compute_deps_files
from biicode.common.exception import BiiException
from biicode.client.command.printers.command_printer import Printer
from biicode.common.utils.bii_logging import logger
from biicode.client.hooks import handle_hooks
import traceback
import shutil
import os
from biicode.common.migrations.biiconfig_migration import delete_migration_files
from biicode.client.workspace.bii_paths import SRC_DIR, DEP_DIR, BII_DIR, BII_HIVE_DB
from biicode.common.utils.file_utils import save
from biicode.common.model.brl.complex_name import ComplexName


def init_hive(bii, project_name=None, layout=None):
    """ Initializes an empty project
    """
    user_cache = bii.user_cache
    out = bii.user_io.out

    bii_paths = bii.bii_paths
    if bii_paths.current_dir.startswith(bii_paths.user_bii_home):
        raise BiiException('Cannot create a project inside the user .biicode folder')

    try:
        bii_paths.project_root
        raise ClientException('Cannot create project inside other project')
    except NotInAHiveException:
        pass

    if project_name:
        name = ComplexName(project_name)
        current_dir = os.path.join(bii_paths.current_dir, name)
        bii_paths.current_dir = current_dir
    else:
        current_dir = bii_paths.current_dir
        ComplexName(os.path.basename(current_dir))

    for root, _, _ in os.walk(current_dir):
        if os.path.exists(os.path.join(root, BII_DIR, BII_HIVE_DB)):
            if root == current_dir:
                project_name = os.path.basename(current_dir)
                raise ClientException('Project "%s" already exists' % project_name)
            raise ClientException('Cannot create project with other project inside:\n%s' % root)

    hive_disk_image = bii.hive_disk_image
    hive_disk_image.initialize()

    try:
        hive_disk_image.hivedb.read_edition_contents()
        out.success('Successfully initialized biicode project %s' % (project_name or ""))
    # If an exception is launched, the hive folder is deleted
    except BaseException as e:
        out.error('An error occurred while creating the project %s' % str(e))
        logger.error(traceback.format_exc())
        if project_name and os.path.exists(current_dir):
            hive_disk_image.hivedb.disconnect()
            shutil.rmtree(current_dir)
    else:
        layout_content = user_cache.layout(layout)
        if layout_content:
            save(os.path.join(hive_disk_image.paths.bii, "layout.bii"), layout_content)


class ClientHiveManager(HiveManager):
    """ The main entry point for business logic in client
    """
    def __init__(self, bii):
        self.bii = bii
        self.user_io = self.bii.user_io
        self.hive_disk_image = self.bii.hive_disk_image
        super(ClientHiveManager, self).__init__(self.hive_disk_image.hivedb, bii.biiapi,
                                                bii.user_io.out)

    @property
    def paths(self):
        return self.hive_disk_image.paths

    def _process(self):
        """ always the first step in every command
        """
        files = self.hive_disk_image.get_src_files()
        settings = self.hive_disk_image.settings
        self.user_io.out.info('Processing changes...')
        deleted_migration = self.process(settings, files)
        delete_migration_files(deleted_migration, self.hive_disk_image.paths.blocks)
        self._checkout()
        self._checkout_deps()

    def work(self):
        self._process()
        self._handle_hooks('post_proc')

    def _handle_hooks(self, stage):
        """ will manage user defined hooks. It has a problem, it works only if
        project is processed. So for clean, it has to detect if there are hooks,
        then execute a work first
        """
        handle_hooks(stage, self.hive_holder, self.closure, self.bii)

    def _checkout(self, allow_delete_block=None):
        '''
        Checks-out HiveDB into disk
        Params:
            delete: BlockName or None
                    if BlockName it will delete that block_name
        ''' 
        if allow_delete_block:
            self.hive_disk_image.delete_removed(SRC_DIR, self.hive_holder.resources,
                                                block_filter=allow_delete_block)
        settings = self.hive_disk_image.settings
        update_files = compute_files(self.hive_holder, self.user_io.out, settings)
        self.hive_disk_image.save(SRC_DIR, update_files)

    def _checkout_deps(self):
        if self.closure is not None:
            files = compute_deps_files(self.closure)
            if files:
                self.hive_disk_image.save(DEP_DIR, files)
            self.hive_disk_image.delete_removed(DEP_DIR, files)

    def new(self, block_name=None, hello_lang=None):
        root_block = self.hive_disk_image.paths.root_block
        auto_root_path = self.hive_disk_image.paths.auto_root_block

        if block_name and not block_name == root_block:
            new_block_path = self.hive_disk_image.create_new_block(block_name)
        elif auto_root_path or root_block:
            new_block_path = self.hive_disk_image.paths.project_root
        else:
            raise ClientException("Too few arguments, specify a block name "
                                  "or add in your lauout.bii auto-root-path: True "
                                  "or a root-block: my_user/my_block")

        # If user has entered -- hello cpp, we create a main file with hello world cpp template
        if hello_lang:
            from biicode.client.dev.wizards import get_main_file_template
            hello_lang = ''.join(hello_lang)
            file_name, content = get_main_file_template(hello_lang)
            self.hive_disk_image.create_new_file(new_block_path, file_name, content)

    def clean(self):
        # TODO: Check that there are no changes in deps
        if self.hive_disk_image.clean_hooks():
            self._process()
            self._handle_hooks('clean')
        self.hive_disk_image.clean()

    def publish(self, block_name, tag, msg, versiontag, publish_all, origin):
        self._process()
        parents = [b.parent for b in self.hive_holder.block_holders if b.parent.time != -1]
        self.bii.biiapi.check_valid(parents)

        HiveManager.publish(self, block_name, tag, msg, versiontag,
                            publish_all=publish_all, origin=origin)
        self._checkout()
        # Check again, in case some parent outdated DEV => STABLE
        parents = [b.parent for b in self.hive_holder.block_holders if b.parent.time != -1]
        self.bii.biiapi.check_valid(parents, publish=False)

    def find(self, **find_args):
        self._process()
        try:
            policies = self.hive_disk_image.policies
            find_result = super(ClientHiveManager, self).find(policies, **find_args)
            Printer(self.user_io.out).print_find_result(find_result)
            self.apply_find_result(find_result)
            self._checkout()
            self._checkout_deps()
        except ConnectionErrorException:
            self.user_io.out.error('Unable to connect to server to find deps')

    def update(self, block, time):
        self._process()
        parents = [b.parent for b in self.hive_holder.block_holders if b.parent.time != -1]
        self.bii.biiapi.check_valid(parents, publish=False)
        block = super(ClientHiveManager, self).update(self.hive_disk_image.settings, block, time)
        self._checkout(allow_delete_block=block)
        self._checkout_deps()

    def open(self, block_name, track, time, version_tag):
        '''
        Params:
            block_version. It time is None last version will be retrieved
        '''
        self._process()
        opened_version = HiveManager.open(self, block_name, track, time, version_tag)
        self._checkout()
        self._checkout_deps()
        if os.path.exists(os.path.join(self.hive_disk_image.paths.deps, block_name)):
            raise BiiException("Unable to remove %s from 'deps' folder. Maybe there exist "
                               "temporary files, or some file is locked by other "
                               "application. Check it and delete manually 'deps/%s' folder."
                               % (block_name, block_name))
        self.bii.user_io.out.write('Opened %s\n' % str(opened_version))

    def close(self, block_name, force):
        self._process()
        HiveManager.close(self, block_name, self.hive_disk_image.settings, force)
        self._checkout(allow_delete_block=block_name)
        self._checkout_deps()  # When closing a block we might have less dependencies
        if os.path.exists(os.path.join(self.hive_disk_image.paths.blocks, block_name)):
            raise BiiException("Unable to remove %s from '%s' folder. Maybe there exist "
                               "temporary or ignored files, or some file is locked by an open "
                               "application. Check it and delete manually 'blocks/%s' folder."
                               % (block_name, SRC_DIR, block_name))
        self.bii.user_io.out.write('%s closed\n' % block_name)

    def diff(self, block_name, version_child, version_parent, short):
        from biicode.client.command.printers.diff_printer import print_diff
        self._process()
        print_diff(self.bii.user_io.out,
                   self.hive_holder,
                   self._biiapi,
                   block_name,
                   version_child,
                   version_parent,
                   short)

    def deps(self, block_name=None, details=False, files=False):
        ''' Command to show all the dependencies in a project '''
        from biicode.client.command.printers.deps_printer import print_deps
        self._process()
        print_deps(self.bii.user_io.out, self.hive_holder, block_name, details, files)
