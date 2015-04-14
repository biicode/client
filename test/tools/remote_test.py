import unittest
from biicode.common.model.resource import Resource
from nose.plugins.attrib import attr
from biicode.common.model.symbolic.reference import References


@attr('remote')
class RemoteTest(unittest.TestCase):

    def assert_published_resources(self, api_manager, version, files):
        """
        :param version: BlockVersion published
        :files: dict of {path_to_file: str_bytes}"""
        cellnames = {blockcellname.cell_name: content
                     for blockcellname, content in files.iteritems()}
        refs = References()
        refs[version] = set(cellnames.keys())
        referenced_resources = api_manager.get_published_resources(refs)
        for thefile, thecontent in cellnames.iteritems():
            resource = referenced_resources[version][thefile]
            self.assertIsInstance(resource, Resource)
            self.assertEqual(resource.content.load.text, thecontent)
