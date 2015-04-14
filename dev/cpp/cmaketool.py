import os
from biicode.client.dev.cmake.cmaketool import CMakeTool
from biicode.common.model.blob import Blob
from biicode.common.utils.file_utils import save_blob_if_modified, save, load_resource
from biicode.client.dev.cpp import DEV_CPP_DIR


default_cmake = """
ADD_BII_TARGETS()

###############################################################################
#      HELP                                                                   #
###############################################################################
#
# This CMakeLists.txt file helps defining your block builds
# To learn more visit http://docs.biicode.com/c++.html
#
# To include published cmake scripts:
#   1. INCLUDE(user/block/myrecipe) # include myrecipe.cmake from remote user/block
#   2. Remember to execute bii find
#   Example:
#      INCLUDE(biicode/cmake/tools) # Include tools.cmake file from cmake block from "biicode" user
#      ACTIVATE_CPP11(INTERFACE ${BII_BLOCK_TARGET})
#
# Useful variables:
#   To be modified BEFORE the call to ADD_BII_TARGETS()
#     ${BII_LIB_SRC}  File list to create the library
#
#   To be modified AFTER the call to ADD_BII_TARGETS()
#     ${BII_BLOCK_TARGET}  Interface (no files) target for convenient configuration of all
#                          targets in this block, as the rest of targets always depend on it
#                          has name in the form "user_block_interface"
#     ${BII_LIB_TARGET}  Target library name, usually in the form "user_block". May not exist
#                        if BII_LIB_SRC is empty
#     ${BII_BLOCK_TARGETS} List of all targets defined in this block
#     ${BII_BLOCK_EXES} List of executables targets defined in this block
#     ${BII_exe_name_TARGET}: Executable target (e.g. ${BII_main_TARGET}. You can also use
#                            directly the name of the executable target (e.g. user_block_main)
#
# > EXAMPLE: Add include directories to all targets of this block
#
#    TARGET_INCLUDE_DIRECTORIES(${BII_BLOCK_TARGET} INTERFACE myincludedir)
#
# > EXAMPLE: Link with pthread:
#
#    TARGET_LINK_LIBRARIES(${BII_BLOCK_TARGET} INTERFACE pthread)
#        or link against library:
#    TARGET_LINK_LIBRARIES(${BII_LIB_TARGET} PUBLIC pthread)
#
#    NOTE:  This can be also done adding pthread to ${BII_LIB_DEPS}
#            BEFORE calling ADD_BIICODE_TARGETS()
#
# > EXAMPLE: how to activate C++11
#
#    IF(APPLE)
#         TARGET_COMPILE_OPTIONS(${BII_BLOCK_TARGET} INTERFACE "-std=c++11 -stdlib=libc++")
#    ELSEIF (WIN32 OR UNIX)
#         TARGET_COMPILE_OPTIONS(${BII_BLOCK_TARGET} INTERFACE "-std=c++11")
#    ENDIF(APPLE)
#
# > EXAMPLE: Set properties to target
#
#    SET_TARGET_PROPERTIES(${BII_BLOCK_TARGET} PROPERTIES COMPILE_DEFINITIONS "IOV_MAX=255")
#


"""


class CPPCMakeTool(CMakeTool):

    def _get_project_cmakelists(self, block_targets):
        cmakelists_template = load_resource(DEV_CPP_DIR, "cmake/CMakeLists.txt")

        blocks_include = []
        blocks_prebuild_step = []

        root_block = self.bii_paths.root_block
        CMAKELISTS_INCLUDES = "BII_INCLUDE_BLOCK({path_block_name})"
        CMAKELISTS_PREBUILD = "BII_PREBUILD_STEP({path_block_name})"
        for block_name, block_target in block_targets.iteritems():
            if block_target.is_dep:
                rel_block_path = self.bii_paths.deps_relative
            else:
                rel_block_path = self.bii_paths.blocks_relative
            if block_name == root_block:
                block_path = root_block
            else:
                block_path = os.path.join(rel_block_path, block_target.block_name).replace('\\',
                                                                                           '/')
            blocks_include.append(CMAKELISTS_INCLUDES.format(path_block_name=block_path))
            blocks_prebuild_step.append(CMAKELISTS_PREBUILD.format(path_block_name=block_path))

        biicode_env_dir = self.bii_paths.user_bii_home.replace('\\', '/')
        return cmakelists_template.format(project_name=self.bii_paths.project_name,
                                          prebuild_steps="\n".join(blocks_prebuild_step),
                                          include_blocks="\n".join(blocks_include),
                                          biicode_env_dir=biicode_env_dir,
                                          blocks=self.bii_paths.blocks_relative,
                                          deps=self.bii_paths.deps_relative,
                                          cmake=self.bii_paths.cmake_relative,
                                          bin=self.bii_paths.bin_relative,
                                          lib=self.bii_paths.lib_relative,
                                          project_root=self.bii_paths.project_root.replace('\\',
                                                                                           '/'))

    def _create_vars_cmake_files(self, block_targets):
        b = False
        for block_target in block_targets.itervalues():
            bii_vars_path = os.path.join(self.bii_paths.cmake, block_target.filename)
            modified = save_blob_if_modified(bii_vars_path, Blob(block_target.dumps()))
            b = b or modified
        return b

    def _create_default_blocks_cmakelists(self, block_targets):
        # create default cmakelists
        project_block = self.bii_paths.root_block
        for block_name, block_target in block_targets.iteritems():
            path_folder = self.bii_paths.deps if block_target.is_dep else self.bii_paths.blocks
            if block_name == project_block:
                cmakelists_path = os.path.join(self.bii_paths.project_root, "CMakeLists.txt")
            else:
                cmakelists_path = os.path.join(path_folder, block_name, "CMakeLists.txt")
            cmakelists_path = cmakelists_path.replace('\\', '/')  # replace in win32
            if not os.path.exists(cmakelists_path):
                save(cmakelists_path, default_cmake)

    def _create_cmakelists(self, block_targets):
        '''creates 3 files:
        CMakeLists.txt, only if not existing, including the other two files
        bii_targets.cmake, the file containing the ADD_LIBRARY and ADD_EXECUTABLES, with the
                        configuration of flags per target and files
        bii_vars.cmake, is a file with variables declarations that are afterwards used in
                        bii_targets.cmake'''
        cmakelists_path = os.path.join(self.bii_paths.cmake, "CMakeLists.txt")
        bii_macros_path = os.path.join(self.bii_paths.cmake, 'biicode.cmake')
        bii_macros_content = load_resource(DEV_CPP_DIR, "cmake/biicode.cmake")

        self._create_default_blocks_cmakelists(block_targets)
        # following is a virtual call, may call child class method
        cmakelists_content = self._get_project_cmakelists(block_targets)

        a = save_blob_if_modified(cmakelists_path, Blob(cmakelists_content))
        b = self._create_vars_cmake_files(block_targets)
        c = save_blob_if_modified(bii_macros_path, Blob(bii_macros_content))

        return a or b or c
