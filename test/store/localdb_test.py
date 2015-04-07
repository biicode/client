
from unittest import TestCase
import tempfile
import os
import shutil
from biicode.client.store.localdb import LocalDB, DEP_TABLES
from biicode.common.test.conf import BII_TEST_FOLDER
from biicode.common.model.symbolic.reference import References, ReferencedResources
from biicode.common.model.brl.cell_name import CellName
from biicode.common.model.resource import Resource
from nose.plugins.attrib import attr
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.cells import SimpleCell, VirtualCell
from biicode.common.model.blob import Blob
from biicode.common.model.content import Content
from biicode.common.model.id import ID
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.client.store.sqlite import encode_serialized_value
from biicode.common.exception import NotInStoreException


@attr('integration')
class LocalDBTest(TestCase):
    _suites = ['client']

    def setUp(self):
        self.hiveFolder = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.db = LocalDB(os.path.join(self.hiveFolder, 'bii.db'))

    def tearDown(self):
        if os.path.isdir(self.hiveFolder):
            self.db.disconnect()
            # os.chmod(self.hiveFolder, stat.S_IWRITE)
            shutil.rmtree(self.hiveFolder)

    def test_not_logged_in(self):
        user = self.db.get_login()
        self.assertEquals(user, (None, None))

    def test_logged_in(self):
        user = "dummyname", "dummypass"
        self.db.set_login(user)
        user2 = self.db.get_login()
        self.assertEquals(user, user2)

    def test_store_published_resources(self):
        s = References()
        brl_block = BRLBlock('dummy/dummy/block/master')
        block_version = BlockVersion(brl_block, 0)
        s[block_version] = [CellName("alf.c"), CellName("willy.c"),
                            CellName('maya.h'), CellName('win/maya.h'), CellName('nix/maya.h')]

        alf = Resource(SimpleCell("dummy/block/alf.c"),
                       Content(ID((0, 1, 2)), Blob("Hello Alf")))
        alf.cell.ID = ID((0, 1, 2))
        willy = Resource(SimpleCell("dummy/block/willy.c"),
                         Content(ID((0, 1, 3)), Blob("Hello Willy")))
        willy.cell.ID = ID((0, 1, 45))
        maya_v = Resource(VirtualCell("dummy/block/maya.h"), None)
        maya_v.cell.ID = ID((0, 1, 3))
        maya_win = Resource(SimpleCell("dummy/block/win/maya.h"),
                            Content(ID((0, 1, 4)), Blob("Hello Maya")))
        maya_win.cell.ID = ID((0, 1, 4))
        maya_nix = Resource(SimpleCell("dummy/block/nix/maya.h"),
                            Content(ID((0, 1, 5)), Blob("Hello Maya")))
        maya_nix.cell.ID = ID((0, 1, 5))

        # Expected return
        referenced_resources = ReferencedResources()
        referenced_resources[block_version].update({CellName("alf.c"): alf,
                                                    CellName("willy.c"): willy,
                                                    CellName('maya.h'): maya_v,
                                                    CellName('win/maya.h'): maya_win,
                                                    CellName('nix/maya.h'): maya_nix,
                                                    })

        self.db.create_published_resources(referenced_resources)
        retrieved = self.db.get_published_resources(s)

        self.assertEquals(referenced_resources, retrieved)

    def test_store_snapshot(self):
        original_snap = [CellName("alf.c"), CellName("willy.c")]
        brl_block = BRLBlock('dummy/dummy/block/master')
        block_version = BlockVersion(brl_block, 0)
        self.db.create_cells_snapshot(block_version, original_snap)
        retrieved_snap = self.db.get_cells_snapshot(block_version)
        self.assertEquals(original_snap, retrieved_snap)

    def test_store_dep_table(self):
        original_deptable = BlockVersionTable()
        brl_block = BRLBlock('dummy/dummy/block/master')
        block_version = BlockVersion(brl_block, 0)
        self.db.set_dep_table(block_version, original_deptable)
        retrieved_snap = self.db.get_dep_table(block_version)
        self.assertEquals(original_deptable, retrieved_snap)

    def test_delete_dep_table(self):
        original_deptable = BlockVersionTable()
        brl_block = BRLBlock('dummy/dummy/block/master')
        block_version = BlockVersion(brl_block, 0)
        self.db.set_dep_table(block_version, original_deptable)
        ID = encode_serialized_value(block_version.serialize())
        self.db.delete(ID, DEP_TABLES)
        self.assertRaises(NotInStoreException, self.db.get_dep_table, block_version)
