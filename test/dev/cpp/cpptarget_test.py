import unittest
from biicode.client.dev.cpp.cpptarget import CPPExeTarget
from biicode.common.model.brl.block_cell_name import BlockCellName


class CPPTargetTest(unittest.TestCase):
    def test_exe(self):
        cpp = CPPExeTarget(BlockCellName("user/block/main.cpp"))
        self.assertEqual(cpp.main, "user/block/main.cpp")
        self.assertEqual(cpp.name, "user_block_main")
        self.assertEqual(cpp.simple_name, "main")
