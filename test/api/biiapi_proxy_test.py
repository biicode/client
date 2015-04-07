
import os
from biicode.common.model.resource import Resource
from biicode.common.model.brl.cell_name import CellName
from biicode.common.model.symbolic.reference import ReferencedResources, References
from mock import Mock
from biicode.client.store.localdb import LocalDB
from biicode.client.api.biiapi_proxy import BiiAPIProxy
from biicode.common.test.bii_test_case import BiiTestCase
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.common.model.content import Content
from biicode.common.model.blob import Blob
from biicode.common.model.id import ID
from biicode.common.model.brl.brl_block import BRLBlock
from biicode.common.model.symbolic.block_version import BlockVersion
from biicode.common.model.cells import SimpleCell
from biicode.common.model.block_delta import BlockDelta
from biicode.common.model.version_tag import DEV
from biicode.common.api.biiapi import BiiAPI


class BiiApiProxyTest(BiiTestCase):

    def setUp(self):
        self.folder = self.new_tmp_folder()

        brl_block = BRLBlock('dummy/dummy/block/master')
        self.block_version = BlockVersion(brl_block, 0)

        alf = Resource(SimpleCell("dummy/block/alf.c"),
                       Content(ID((0, 1, 2)), Blob("Hello Alf")))
        alf.cell.ID = ID((0, 1, 2))
        willy = Resource(SimpleCell("dummy/block/willy.c"),
                         Content(ID((0, 1, 3)), Blob("Hello Willy")))
        willy.cell.ID = ID((0, 1, 45))

        self.referenced_resources = ReferencedResources()
        self.referenced_resources[self.block_version].update({CellName("alf.c"): alf,
                                                              CellName("willy.c"): willy})
        self.cells_snapshot = [CellName("alf.c"), CellName("willy.c")]
        self.dep_table = BlockVersionTable()

        self.restapi = Mock(BiiAPI)
        self.restapi.get_published_resources.return_value = self.referenced_resources
        self.restapi.get_cells_snapshot.return_value = self.cells_snapshot
        self.restapi.get_dep_table.return_value = self.dep_table
        self.restapi.get_version_delta_info.return_value = BlockDelta('', DEV, None)
        self.localdb = LocalDB(os.path.join(self.folder, 'bii.db'))
        self.proxy = BiiAPIProxy(self.localdb, self.restapi, Mock())

    def test_get_version_by_tag(self):
        brl = BRLBlock("user/user/block/master")
        self.proxy.get_version_by_tag(brl, '@mytag')
        self.assertTrue(self.restapi.get_version_by_tag.called)

    def test_cached_references(self):
        s = References()
        s[self.block_version] = {CellName("alf.c"), CellName("willy.c")}

        self.proxy.get_published_resources(s)

        self.assertTrue(self.restapi.get_published_resources.called)
        self.restapi.get_published_resources.called = False

        c = self.proxy.get_published_resources(s)
        self.assertFalse(self.restapi.get_published_resources.called)
        self.assertEqual(c, self.referenced_resources)

    def test_cached_snapshot(self):
        self.proxy.get_cells_snapshot(self.block_version)

        self.assertTrue(self.restapi.get_cells_snapshot.called)
        self.restapi.get_cells_snapshot.called = False

        snap = self.proxy.get_cells_snapshot(self.block_version)
        self.assertFalse(self.restapi.get_cells_snapshot.called)
        self.assertEqual(self.cells_snapshot, snap)

    def test_cached_dep_table(self):
        self.proxy.get_dep_table(self.block_version)

        self.assertTrue(self.restapi.get_dep_table.called)
        self.restapi.get_dep_table.called = False

        snap = self.proxy.get_dep_table(self.block_version)
        self.assertFalse(self.restapi.get_dep_table.called)
        self.assertEqual(self.dep_table, snap)
