import os
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.model.bii_type import BiiType


def _binary_name(name):
    return os.path.splitext(name.replace("/", "_"))[0]


class CPPTarget(object):

    def __init__(self):
        self.files = set()  # The source files in this target
        self.dep_targets = set()  # set of BlockNames, to which this target depends
        self.system = set()  # These are the included system headers (stdio.h, math.h...)
        self.include_paths = {}  # Initially {Order#: BlockNamePath}. At the end [FullPaths]

    @property
    def dep_names(self):
        return sorted([_binary_name(d) for d in self.dep_targets])


class CPPLibTarget(CPPTarget):
    template = """
# LIBRARY {library_name} ##################################
# with interface {library_name}_interface

# Source code files of the library
SET(BII_LIB_SRC  {files})
# STATIC by default if empty, or SHARED
SET(BII_LIB_TYPE {type})
# Dependencies to other libraries (user2_block2, user3_blockX)
SET(BII_LIB_DEPS {library_name}_interface {deps})
# System included headers
SET(BII_LIB_SYSTEM_HEADERS {system})
# Required include paths
SET(BII_LIB_INCLUDE_PATHS {paths})

"""

    def __init__(self, block_name):
        CPPTarget.__init__(self)
        self.name = _binary_name(block_name)
        self.type = ""  # By default, libs are static

    def dumps(self):
        content = CPPLibTarget.template.format(library_name=self.name,
                                               files="\n\t\t\t".join(sorted(self.files)),
                                               type=self.type,
                                               deps=" ".join(self.dep_names),
                                               system=" ".join(sorted(self.system)),
                                               paths="\n\t\t\t\t\t".join(self.include_paths))
        return content


class CPPExeTarget(CPPTarget):
    template = """
# EXECUTABLE {exe_name} ##################################

SET(BII_{exe_name}_SRC {files})
SET(BII_{exe_name}_DEPS {block_interface} {deps})
# System included headers
SET(BII_{exe_name}_SYSTEM_HEADERS {system})
# Required include paths
SET(BII_{exe_name}_INCLUDE_PATHS {paths})
"""

    def __init__(self, main):
        CPPTarget.__init__(self)
        assert isinstance(main, BlockCellName)
        assert not BiiType.isCppHeader(main.extension)
        self.main = main
        self.files.add(main.cell_name)
        self.name = _binary_name(main)
        self.block_interface = _binary_name(main.block_name) + "_interface"
        self.simple_name = _binary_name(main.cell_name)

    def dumps(self):
        content = CPPExeTarget.template.format(block_interface=self.block_interface,
                                               exe_name=self.simple_name,
                                               files="\n\t\t\t".join(sorted(self.files)),
                                               deps=" ".join(self.dep_names),
                                               system=" ".join(sorted(self.system)),
                                               paths="\n\t\t\t\t\t".join(self.include_paths))
        return content


class CPPBlockTargets(object):
    """ All the targets defined in a given block:
    - 1 Lib
    - N Exes
    - There is always an Interface Lib per block, but no parametrization required here
    """
    def __init__(self, block_name):
        self.block_name = block_name
        self.is_dep = False  # To indicate if lives in deps or blocks folder
        self.data = set()
        self.lib = CPPLibTarget(block_name)
        self.exes = []  # Of CPPExeTargets
        self.tests = set()  # Of CPPExeTargets

    @property
    def filename(self):
        return "bii_%s_vars.cmake" % _binary_name(self.block_name)

    def dumps(self):
        exe_list = """# Executables to be created
SET(BII_BLOCK_EXES {executables})

SET(BII_BLOCK_TESTS {tests})
"""
        vars_content = ["# Automatically generated file, do not edit\n"
                        "SET(BII_IS_DEP %s)\n" % self.is_dep]
        vars_content.append(self.lib.dumps())
        exes = [t.simple_name for t in self.exes]
        tests = [t.simple_name for t in self.tests]
        exes_list = exe_list.format(executables="\n\t\t\t".join(sorted(exes)),
                                    tests="\n\t\t\t".join(sorted(tests)))
        vars_content.append(exes_list)
        for exe in self.exes:
            content = exe.dumps()
            vars_content.append(content)
        return "\n".join(vars_content)
