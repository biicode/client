import argparse
from biicode.client.dev.node.runners_tools import create_noderunner
from biicode.common.output_stream import Color


class NodeToolChain(object):
    """Commands for node programming"""
    group = 'node'

    def __init__(self, bii):
        self.bii = bii

    def settings(self, *parameters):
        '''Configure project settings and runner for node.js'''
        parser = argparse.ArgumentParser(description=self.settings.__doc__,
                                         prog="bii %s:settings" % self.group)
        parser.parse_args(*parameters)  # for -h
        bii_paths = self.bii.bii_paths
        self.bii.user_io.out.writeln("Creating noderunner script with paths to code folders",
                                     Color.BRIGHT_GREEN)
        create_noderunner(bii_paths.project_root, bii_paths.blocks, bii_paths.deps)
