
import unittest
from biicode.client.shell.biistream import BiiOutputStream
from biicode.client.command.tool_catalog import ToolCatalog
from biicode.client.command.biicommand import BiiCommand
from biicode.client.dev.cpp.cpptoolchain import CPPToolChain
from StringIO import StringIO


class ToolCatalogtext(unittest.TestCase):

    def test_help(self):
        mystdout = StringIO()
        out = BiiOutputStream(stream=mystdout)
        toolcatalog = ToolCatalog(BiiCommand, tools=[CPPToolChain])
        toolcatalog.show_advanced = True

        argv = ["all"]
        #Must print all
        mystdout.truncate(0)
        toolcatalog.print_help(out, argv)
        self.assertIn("cmake --build.", str(mystdout.buflist))

        #Must NOT print all
        mystdout.truncate(0)
        argv = None
        toolcatalog.print_help(out, argv)
        self.assertNotIn("cmake --build.", str(mystdout.buflist))

        #Must NOT print all
        mystdout.truncate(0)
        argv = []
        toolcatalog.print_help(out, argv)
        self.assertNotIn("cmake --build.", str(mystdout.buflist))

        #Must print cpp group
        mystdout.truncate(0)
        argv = ["cpp"]
        toolcatalog.print_help(out, argv)
        self.assertIn("cmake --build.", str(mystdout.buflist))
