
import unittest
from biicode.client.command.executor import ToolExecutor
from mock import Mock
from biicode.client.command.tool_catalog import ToolCatalog
from biicode.client.dev.cpp.cpptoolchain import CPPToolChain
from biicode.client.command.biicommand import BiiCommand
import biicode.common
from biicode.client.shell.userio import UserIO
from biicode.client.shell.bii import Bii
from biicode.client.shell.biistream import BiiOutputStream
from biicode.client.exception import ClientException


class ToolExecutortext(unittest.TestCase):
    def test_tool_executor(self):
        bii = Bii(UserIO(out=BiiOutputStream()), "dummy_current_folder", "dummy_user_folder")
        toolcatalog = ToolCatalog(BiiCommand, tools=[CPPToolChain])
        toolcatalog.print_help = Mock(return_value=True)
        tool = ToolExecutor(bii, toolcatalog)
        #Effective call
        tool._call_method = Mock(return_value=True)

        # --quiet
        argv = ["cpp:configure", "--quiet"]
        tool.execute(argv)
        self.assertEqual(bii.user_io.out.level, 2)

        # --verbose
        argv = ["cpp:configure", "--verbose"]
        tool.execute(argv)
        self.assertEqual(bii.user_io.out.level, 0)

        # --version
        argv = ["--version"]
        tool.execute(argv)
        self.assertIn("%s\n" % biicode.common.__version__, str(bii.user_io.out))

        # --help
        argv = ["--help"]
        tool.execute(argv)
        toolcatalog.print_help.assert_called_with(bii.user_io.out, [])

        # Bad command
        argv = ["paspas"]
        self.assertRaises(ClientException, tool.execute, argv)
