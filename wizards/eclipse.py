import os
import platform
from xml.etree import ElementTree
from biicode.common.utils import file_utils
from biicode.client.workspace.bii_paths import SRC_DIR


XML_HEADER = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?fileVersion 4.0.0?>
'''

OSX_BINARY_PARSER = '''<extension id="org.eclipse.cdt.core.MachO64" point="org.eclipse.cdt.core.BinaryParser"/>'''

LINKED_RESOURCES = '''
<linkedResources>
<link>
    <name>[CMake directory]</name>
    <type>2</type>
    <location>{0}</location>
</link>
<link>
    <name>[Bin directory]</name>
    <type>2</type>
    <location>{1}</location>
</link>
<link>
    <name>blocks</name>
    <type>2</type>
    <location>{2}</location>
</link>
<link>
    <name>bii</name>
    <type>2</type>
    <location>{3}</location>
</link>
<link>
    <name>deps</name>
    <type>2</type>
    <location>{4}</location>
</link>
</linkedResources>
'''

SRC_TYPE_DIR = '<pathentry kind="src" path="blocks"/>'
DEP_TYPE_DIR = '<pathentry kind="src" path="deps"/>'


class Eclipse(object):
    '''This class is in charge of configuring eclipse project'''

    def __init__(self, paths):
        '''
        Params:
            build_path: Path to hive build folder, where eclipse files are located
        '''
        self.paths = paths

    def configure_project(self):
        self._add_build_step()
        self._add_linked_resources()
        self._add_src_dir_type()

    def _add_build_step(self):
        project_config = self._project_config_path()
        contents = file_utils.load(project_config)

        if '-Debug' in contents:
            file_utils.search_and_replace(project_config, '-Debug@build</name>', '@build</name>')

    def _project_config_path(self, filename='.project'):
        project_config = os.path.join(self.paths.build, filename)
        return project_config

    def _add_linked_resources(self):
        project_config = self._project_config_path()

        cmake_path = self.paths.cmake.replace('\\', '/')
        bin_path = self.paths.bin.replace('\\', '/')
        blocks_path = self.paths.blocks.replace('\\', '/')
        deps_path = self.paths.deps.replace('\\', '/')
        bii_path = self.paths.bii.replace('\\', '/')
        linked_resources_xml = LINKED_RESOURCES.format(cmake_path, bin_path, blocks_path, bii_path,
                                                       deps_path)

        tree = ElementTree.fromstring(file_utils.load(project_config))

        link_names = tree.findall('linkedResources/*name')

        if not any(link_name.text == SRC_DIR for link_name in link_names):
            links_tree = ElementTree.fromstring(linked_resources_xml)
            linked_resources = tree.find(".//linkedResources")
            linked_resources.clear()
            for link in links_tree:
                linked_resources.append(link)
            et = ElementTree.ElementTree(tree)
            et.write(project_config, encoding='utf-8', xml_declaration=True)

    def _add_src_dir_type(self):
        cproject_config = self._project_config_path('.cproject')
        tree = ElementTree.parse(cproject_config)

        if not tree.find(".//storageModule[@moduleId='org.eclipse.cdt.core.pathentry']/*[@path='blocks']"):
            storage_module = tree.find(".//storageModule[@moduleId='org.eclipse.cdt.core.pathentry']")
            src_type_element = ElementTree.fromstring(SRC_TYPE_DIR)
            storage_module.append(src_type_element)
            dep_type_element = ElementTree.fromstring(DEP_TYPE_DIR)
            storage_module.append(dep_type_element)
            tree.write(cproject_config)
            cproject_string = file_utils.load(cproject_config)
            cproject_string = "%s%s" % (XML_HEADER, cproject_string)
            file_utils.save(cproject_config, cproject_string)

    def _add_osx_binary_parser(self):
        if platform.system() == 'Darwin':
            cproject_config = self._project_config_path('.cproject')
            tree = ElementTree.parse(cproject_config)
            if not tree.find(".//storageModule[@moduleId='org.eclipse.cdt.core.settings'][@name='Configuration']/*extension[@id='org.eclipse.cdt.core.MachO64']"):
                extensions_node = tree.find(".//storageModule[@moduleId='org.eclipse.cdt.core.settings'][@name='Configuration']//extensions")

                extensions_node.clear()

                binary_parser_node = ElementTree.fromstring(OSX_BINARY_PARSER)
                extensions_node.append(binary_parser_node)
                tree.write(cproject_config)
