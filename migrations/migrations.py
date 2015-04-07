from biicode.common.migrations.migration import Migration
import os
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.utils.file_utils import save
from biicode.client.workspace.bii_paths import BII_DIR


######### DO NOT DELETE *NEVER* A CLASS FROM THIS MODULE ##########
### MIGRATION MANAGER WILL EXECUTE ALL -NOT- EXECUTED MIGRATIONS ##
###################################################################


class MigrateArduinoSettings(Migration):
    '''FIXES OLD ARDUINO SETTINGS IF DETECTED'''

    def migrate(self, *args, **kwargs):
        pass


class MigrateToFirstVersion(Migration):
    '''UPDATES OLD BIICODE HIVES IF DETECTED'''

    def migrate(self, *args, **kwargs):
        bii = args[0]
        disk = bii.hive_disk_image
        disk.clean()
        for root, _, _ in os.walk(disk._bii_paths.blocks):
            relative_root = root.replace(disk._bii_paths.blocks + os.sep, '')
            if len(relative_root.split(os.sep)) == 2:
                block = BlockVersion.loads(relative_root.replace(os.sep, '/')).block
                version = bii.biiapi.get_block_info(block).last_version
                if version.time > -1:
                    file_path = os.path.join(root, BII_DIR, 'parents.bii')
                    save(file_path, '*%s' % version.to_pretty())


def get_client_migrations():
    # DO NOT DELETE **NEVER** ELEMENTS IN THIS LIST. ONLY APPEND NEW MIGRATIONS!!
    return [
            MigrateArduinoSettings(),
            MigrateToFirstVersion(),
    ]
