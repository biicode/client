from biicode.common.exception import NotInStoreException


class MigrationStore(object):

    def __init__(self, hivedb):
        self.hivedb = hivedb

    def store_executed_migration(self, migration):
        self.hivedb.upsert_last_migrated(migration)

    def read_last_migrated(self):
        try:
            return self.hivedb.read_last_migrated()
        except NotInStoreException:
            return None
