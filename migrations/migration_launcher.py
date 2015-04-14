from biicode.common.migrations.migration_manager import MigrationManager
from biicode.client.store.migration_store import MigrationStore
from biicode.client.migrations.migrations import get_client_migrations


def launch(bii):
    disk = bii.hive_disk_image
    migration_store = MigrationStore(disk.hivedb)
    manager = MigrationManager(migration_store, get_client_migrations(), bii.user_io.out)

    # Pass in kwargs all variables migrations can need
    manager.migrate(bii)
