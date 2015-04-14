import tempfile
import os
import shutil
from biicode.client.store import hivedb
from unittest import TestCase
from biicode.common.test.conf import BII_TEST_FOLDER
from nose.plugins.attrib import attr
from biicode.client.store.migration_store import MigrationStore
from biicode.common.test.migration.migration_utils import TMigration1, TMigration2


@attr('integration')
class MigrationStoreTest(TestCase):
    _suites = ['client']
    _multiprocess_shared_ = True

    def setUp(self):
        self.hiveFolder = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.hivedb = hivedb.factory(os.path.join(self.hiveFolder, "mytestdb.db"))
        self.db = MigrationStore(self.hivedb)

    def tearDown(self):
        if os.path.isdir(self.hiveFolder):
            self.hivedb.disconnect()
            try:  # Avoid windows crashes
                shutil.rmtree(self.hiveFolder)
            except Exception:
                pass

    def test_read_and_write_migrations(self):
        mig1 = TMigration1()
        self.db.store_executed_migration(mig1)

        self.assertEquals(self.db.read_last_migrated(), mig1)
        mig2 = TMigration2()
        self.db.store_executed_migration(mig2)

        self.assertEquals(self.db.read_last_migrated(), mig2)
