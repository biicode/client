from biicode.client.dev.cpp.cpptarget import CPPBlockTargets, CPPExeTarget
from biicode.common.model.bii_type import CPP
from biicode.client.dev.mains import compute_mains
from collections import defaultdict, Counter, OrderedDict
from biicode.common.utils.file_utils import save_blob_if_modified
import os
from biicode.common.model.brl.block_cell_name import BlockCellName
from fnmatch import fnmatch
from biicode.client.workspace.bii_paths import DEP_DIR, SRC_DIR
from biicode.common.model.cells import VirtualCell


class CPPTargetProcessor(object):

    def __init__(self, client_hive_manager):
        self.client_hive_manager = client_hive_manager
        self.user_io = client_hive_manager.user_io

    def targets(self):
        '''Main entry point for computing targets
        return: list of CPPTargets, ready to be converted to CMakeLists without further
            processing
        '''
        hive_holder = self.client_hive_manager.hive_holder
        resources = hive_holder.resources
        closure = self.client_hive_manager.closure
        test_patterns = {b.block_name: b.tests for b in hive_holder.block_holders}

        for block_cell_name, (resource, _) in closure.iteritems():
            resources[block_cell_name] = resource

        # Compute the targets, high level
        mains = compute_mains(hive_holder.hive.settings, resources, self.user_io.out)
        block_targets = self._define_targets(mains, resources, test_patterns,
                                             hive_holder.hive.settings)
        self._order_include_paths(block_targets, hive_holder)
        self._define_system_includes(block_targets, mains)
        self._mark_deps(block_targets, hive_holder)
        self._check_not_required_libs(block_targets)
        self._copy_data(block_targets, resources)
        ordered_targets = self._order_by_level(block_targets)
        return ordered_targets

    def _order_by_level(self, block_targets):
        """ The targets must be ordered by level to the PRE_BUILD_STEP. If executed in
        order, downstream targets settings execute later and thus have priority
        """
        graph = self.client_hive_manager.hive_holder.hive_dependencies.version_graph
        levels = graph.get_levels()
        ordered_targets = OrderedDict()
        for level in levels:
            for bversion in level:
                try:
                    # target might not exist, if not sources (only data, CMakes...)
                    ordered_targets[bversion.block_name] = block_targets[bversion.block_name]
                except KeyError:
                    pass
        return ordered_targets

    def _copy_data(self, block_targets, resources):
        """ Data dependencies are copied to the BIN folder of the project, with the
        same relative block_name path
        """
        for block_target in block_targets.itervalues():
            for data in block_target.data:
                r = resources[data]
                datapath = os.path.join(self.client_hive_manager.paths.bin, data)
                save_blob_if_modified(datapath, r.content.load)

    def _mark_deps(self, block_targets, hive_holder):
        # Mark as in "deps" or not
        hive_dependencies = hive_holder.hive_dependencies
        for v in hive_dependencies.dep_graph.nodes:
            if v.block_name in block_targets:
                block_targets[v.block_name].is_dep = True
        return block_targets

    def _define_system_includes(self, block_targets, mains):
        """ system include are assigned to each target. They can be used to deduce
        required system libraries (winmm.lib, pthread...)
        """
        system_includes = defaultdict(set)
        for main in mains.itervalues():
            for name, deps in main.system_includes.iteritems():
                system_includes[name].update(deps)
        for _, target in block_targets.iteritems():
            lib_system_libs = system_includes.get(target.block_name)
            if lib_system_libs:
                target.lib.system.update(lib_system_libs)

    def _check_not_required_libs(self, block_targets):
        """ for simple cases, we dont want to actually build a library, confusing
        for the user. If only 1 EXE, and nobody depends on the block code, then
        we can ommit the library, that finally happens to remain as INTERFACE
        only to account and propagate other properties
        """
        counter = Counter()
        for target in block_targets.itervalues():
            for t in target.exes:
                for dep in t.dep_targets:
                    if dep != target.block_name:
                        counter[dep] += 2
                    else:
                        counter[dep] += 1
            for dep in target.lib.dep_targets:
                counter[dep] += 2
        for target in block_targets.itervalues():
            if target.is_dep:
                continue
            if counter[target.block_name] <= 1:  # not required by anybody else
                # remove from the lib, put files in the exe
                for exe in target.exes:
                    if target.block_name in exe.dep_targets:
                        exe.files.update(target.lib.files)
                        break
                target.lib.files = set()

    def _order_include_paths(self, block_targets, hive_holder):
        """ Up to now, the include paths have been just stored in the dict. Here
        we efectively order them by keys to keep order originally defined in biicode.conf
        (which can't be used, as is not always there in deps), and also take the full
        path, using the CMAKE_HOME_DIRECTORY, and knowing if the path is deps or not
        """
        bii_paths = self.client_hive_manager.paths
        root_block = bii_paths.root_block

        def order_paths(target):
            include_paths = []
            blocks = hive_holder.blocks
            for key in sorted(target.include_paths.iterkeys()):
                path = target.include_paths[key]
                try:
                    current_block = BlockCellName("%s/dummy" % path).block_name
                except:  # Not able to build block_name, it should be only username
                    origins = [DEP_DIR, SRC_DIR]
                    current_block = "&*NoBlock%$"
                else:
                    origins = [SRC_DIR if current_block in blocks else DEP_DIR]
                for src in origins:
                    if src == SRC_DIR:
                        rel_path = bii_paths.blocks_relative
                    else:
                        rel_path = bii_paths.deps_relative
                    if root_block == current_block:
                        # remove the initial BlockName from path
                        cmake_path = '${BII_PROJECT_ROOT}/%s' % path[len(current_block):]
                    else:
                        cmake_path = '${BII_PROJECT_ROOT}/%s/%s' % (rel_path, path)
                    if cmake_path not in include_paths:
                        include_paths.append(cmake_path)
            target.include_paths = include_paths

        for _, target in block_targets.iteritems():
            order_paths(target.lib)
            for exe in target.exes:
                order_paths(exe)

    def _define_targets(self, mains, resources, test_patterns, settings):
        '''
        Parameters:
            mains: {BlockCellName: MainInfo}
            resources: {BlockCellName: Resource}
        '''

        targets = {}
        get_target = lambda block_name: targets.setdefault(block_name, CPPBlockTargets(block_name))

        for main, main_info in mains.iteritems():
            # Creation of main target
            main_target = CPPExeTarget(main)
            main_target.system.update(main_info.main_system)
            main_cell = resources[main].cell
            main_target.include_paths.update(main_cell.dependencies.paths)
            cell_block_deps = {t.block_name for t in main_cell.dependencies.targets}
            main_target.dep_targets.update(cell_block_deps)

            block_target = get_target(main.block_name)
            block_target.data.update(main_info.main_data)
            block_target.exes.append(main_target)
            patterns = test_patterns.get(main.block_name, [])
            for pattern in patterns:
                if fnmatch(main.cell_name, pattern):
                    block_target.tests.add(main_target)
                    break

            # assignment of files to lib target
            for block_cell_name in main_info.src:
                block_cell = resources[block_cell_name].cell
                if isinstance(block_cell, VirtualCell):
                    id_ = block_cell.evaluate(settings)
                    block_cell = resources[id_].cell
                paths = block_cell.dependencies.paths
                cell_block_deps = {t.block_name for t in block_cell.dependencies.targets
                                   if t.block_name != block_cell_name.block_name}

                if block_cell.type == CPP:
                    # Checking lib targets src pass or not [tests] filter
                    for pattern in patterns:
                        if fnmatch(block_cell_name.cell_name, pattern) \
                           and main.block_name == block_cell_name.block_name:
                            block_target.tests.add(main_target)
                            main_target.files.add(block_cell_name.cell_name)
                            main_target.include_paths.update(paths)
                            main_target.dep_targets.update(cell_block_deps)
                            break
                    else:
                        lib_block_name = block_cell_name.block_name
                        lib_target = get_target(lib_block_name).lib
                        lib_target.files.add(block_cell_name.cell_name)
                        lib_target.include_paths.update(paths)
                        lib_target.dep_targets.update(cell_block_deps)

            # Gathering data
            for block_cell_name in main_info.data:
                target = get_target(block_cell_name.block_name)
                target.data.add(block_cell_name)

        return targets
