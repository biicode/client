from biicode.client.dev.cpp.cmaketool import CPPCMakeTool
from biicode.client.dev.cpp.cpptarget_processor import CPPTargetProcessor
from biicode.client.dev.cmake.cmake_tool_chain import CMakeToolChain


class CPPToolChain(CMakeToolChain):
    '''C/C++ commands'''
    group = 'cpp'

    @property
    def target_processor(self):
        return CPPTargetProcessor

    @property
    def cmake(self):
        return CPPCMakeTool
