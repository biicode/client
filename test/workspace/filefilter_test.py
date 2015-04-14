
import unittest
from biicode.common.model.brl.cell_name import CellName
from biicode.client.workspace.bii_ignore import BiiIgnore


class BiiIgnoreTest(unittest.TestCase):

    def test_ignore(self):
        ig = BiiIgnore.defaults()
        self.assertTrue(ig.ignored('path/to/file.obj'))
        self.assertTrue(ig.ignored('file.o'))
        self.assertTrue(ig.ignored('file.cpp~'))
        self.assertTrue(ig.ignored('path/file.h~'))
        self.assertTrue(ig.ignored('path/.git/file.cpp'))
        self.assertTrue(ig.ignored('path/git/.file'))
        self.assertTrue(ig.ignored('.git/file.cpp'))
        self.assertTrue(ig.ignored('.svn/file.cpp'))
        self.assertTrue(ig.ignored('.classpath'))
        self.assertTrue(ig.ignored('__init__.pyc'))
        self.assertTrue(ig.ignored('.DS_STORE'))

    def test_accept(self):
        ig = BiiIgnore.defaults()
        self.assertFalse(ig.ignored('path/file.patata'))
        self.assertFalse(ig.ignored(CellName('path/to/file.h')))
        self.assertFalse(ig.ignored(CellName('path/to.to/file.h')))
        self.assertFalse(ig.ignored(CellName('file.cpp')))
        self.assertFalse(ig.ignored(CellName('file.inl')))
        self.assertFalse(ig.ignored(CellName('file.ipp')))
        self.assertFalse(ig.ignored(CellName('Dense')))

    def test_ordered_rules(self):
        f = '''#Test comment

    *.c
!pepe.c
    *.py
!pepe.py
*.py'''
        ig = BiiIgnore.loads(f)
        self.assertTrue(ig.ignored('kk.c'))
        self.assertFalse(ig.ignored('pepe.c'))
        self.assertTrue(ig.ignored('file.py'))
        self.assertTrue(ig.ignored('pepe.py'))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
