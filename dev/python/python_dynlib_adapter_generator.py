import os
from biicode.client.dev.cpp.cpptarget_processor import CPPTargetProcessor
from biicode.common.model.bii_type import BiiType
from biicode.common.model.blob import Blob
from biicode.common.utils import file_utils
from biicode.common.utils.bii_logging import logger
import platform
import re
from jinja2 import Template
from biicode.client.dev.python.python_cffi_adapter_template import cffi_template


def get_dll_extension():
    op_sys = platform.system()
    if op_sys == 'Windows':
        return 'dll'
    elif op_sys == 'Darwin':
        return 'dylib'
    else:
        return 'so'


def get_dynlib_name(block):
    return 'lib%s_%s.%s' % (block.user, block.name.replace('/', '_'), get_dll_extension())


def clean_preprocessor_directives(include_content):
    """Cffi doesn't accept preprocessor directives, so headers sould be cleaned before cffi adapter generation."""
    reg = re.compile("^#.+$", re.MULTILINE)
    return reg.sub("", include_content).rstrip()


class PythonDynLibAdapterGenerator(object):

    ADAPTER_FILE_NAME = 'biipyc.py'

    def __init__(self, workspace, paths, user_io):
        self.workspace = workspace
        self.paths = paths
        self.user_io = user_io
        self.template = Template(cffi_template)

    def _read_header_contents(self, headers):
        headers_contents = []
        for header_file in headers:
            header_content = file_utils.load(os.path.join(self.paths.dep, header_file))
            headers_contents.append(clean_preprocessor_directives(header_content.rstrip()))
        return headers_contents

    def _create_py_file(self, py_adapter_file_content, main):
        """Write python file content to src block root if content has changed.
        :param
            py_adapter_file_content: str with python adapter file content.
            main: BlockCellName of main target.
        """
        py_adapter_file_path = os.path.join(self.paths.src, main.block_name,
                                            main.cell_name.path, self.ADAPTER_FILE_NAME)
        file_content = Blob(py_adapter_file_content)

        try:
            old_content = Blob(file_utils.load(py_adapter_file_path))
        except:
            old_content = None

        if file_content != old_content:
            logger.debug("biipyc has changed or was created.")
            file_utils.save(py_adapter_file_path, file_content.load)

    def generate_dynlib_adapter(self):

        db = self.workspace.hivedb

        hive = db.read_hive()
        mains = hive.mains

        graph = hive.block_graph
        dep_blocks = set([x.block_name for x in graph.dep.nodes])

        dynlibs_files = map(get_dynlib_name, dep_blocks)
        for main_name, main in mains.iteritems():
            main_deps = main.dep_code
            headers = [block_cell_name for block_cell_name in main_deps if BiiType.isCppHeader(block_cell_name.extension)]
            headers_contents = self._read_header_contents(headers)
            if headers_contents:
                py_adapter = self.template.render(headers=''.join(headers_contents),
                                                  dynlib_file=dynlibs_files[0])
                self._create_py_file(py_adapter, main_name)

