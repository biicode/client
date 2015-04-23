import tempfile
import os
import shutil
from biicode.client.store import hivedb
from biicode.common.model.brl.block_cell_name import BlockCellName
from unittest import main
from biicode.common.model.bii_type import CPP
from biicode.common.test.conf import BII_TEST_FOLDER
from biicode.common.test import testfileutils as TestFileUtils
from biicode.common.test import model_creator as mother
from nose.plugins.attrib import attr
from biicode.common.test.bii_test_case import BiiTestCase
from biicode.common.model.blob import Blob
from biicode.common.model.content import Content


@attr('integration')
class HiveDBTest(BiiTestCase):
    _suites = ['client']
    _multiprocess_shared_ = True

    def setUp(self):
        self.test_folder = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.db = hivedb.factory(os.path.join(self.test_folder, "mytestdb.db"))

    def tearDown(self):
        if os.path.isdir(self.test_folder):
            self.db.disconnect()
            shutil.rmtree(self.test_folder)

    def test_store_many_contents(self):
        '''This test checks we can manage more than 999 items in edition
        1. Create 1500 cells
        2. Retrieve and check
        3. Update 1500
        4. Delete 1500 '''
        contents = []
        ids = []
        #start_time = time.time()
        num_cells = 1500
        for i in range(num_cells):
            rid = BlockCellName("dummy/geom/sphere%d.cpp" % i)
            ids.append(rid)
            contents.append(Content(id_=rid, load=Blob("Hola")))

        self.db.upsert_edition_contents(contents)
        retrieved = self.db.read_edition_contents()
        self.assertEquals(num_cells, len(retrieved))
        for _, cell in retrieved.iteritems():
            cell.type = CPP

        self.db.upsert_edition_contents(retrieved.values())
        #print time.time() - start_time
        #start_time = time.time()
        retrieved = self.db.read_edition_contents()
        #print time.time() - start_time
        #start_time = time.time()
        self.assertEquals(num_cells, len(retrieved))
        self.db.delete_edition_contents(ids)
        #print time.time() - start_time
        #start_time = time.time()
        retrieved = self.db.read_edition_contents()
        #print time.time() - start_time
        #start_time = time.time()
        '''Recall that read_all retrieve a dict, missing keys if not found'''
        self.assertEquals(0, len(retrieved))

    def test_rw_multi_contents(self):
        rid1 = BlockCellName("dummy/geom/sphere.cpp")
        cell1 = mother.make_content(rid1)
        rid2 = BlockCellName("dummy/geom/sphere.h")
        cell2 = mother.make_content(rid2)

        self.db.upsert_edition_contents([cell1, cell2])
        retrieved1 = self.db.read_edition_contents()
        self.assertEquals({rid1: cell1, rid2: cell2}, retrieved1)

    def testStoreContent(self):
        modified_load = TestFileUtils.load("geom/main.cpp")
        cid = BlockCellName("admin/geom/main.cpp")
        original_content = mother.make_content(cid, CPP)
        original_sha = original_content.load.sha

        self.db.upsert_edition_contents([original_content])
        retrieved1 = self.db.read_edition_contents()[cid]
        self.assertEqual(original_content, retrieved1)
        self.assertEquals(original_sha, retrieved1.sha)

        original_content.set_blob(Blob(modified_load))
        modified_sha = original_content.load.sha

        self.db.upsert_edition_contents([original_content])
        retrieved2 = self.db.read_edition_contents()[cid]
        self.assertEquals(modified_sha, retrieved2.sha)

    def testdelete_content(self):
        TestFileUtils.load("geom/main.cpp")
        cid = BlockCellName("admin/geom/main.cpp")
        content = mother.make_content(cid, CPP)

        self.db.upsert_edition_contents([content])
        self.db.delete_edition_contents([cid])
        with self.assertRaises(KeyError):
            self.db.read_edition_contents()[cid]


if __name__ == "__main__":
    main()
