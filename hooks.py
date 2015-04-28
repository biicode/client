from biicode.common.output_stream import Color
import urllib
import os
import fnmatch
from collections import defaultdict, namedtuple
from biicode.client.checkout.snapshotbuilder import compute_deps_files
from biicode.client.setups.setup_tools import decompress


def _download(out):
    def internal_download(url, filename):
        def dl_progress_callback_cmd(count, block_size, total_size):
            if count % 10 == 0:
                if count % 60 == 0:
                    out.write('%d%%' % (100 * min(count * block_size, total_size) / total_size))
                else:
                    out.write('.')

        if not os.path.exists(filename):
            out.writeln('Download %s' % filename, Color.CYAN)
            out.writeln('from %s' % url, Color.CYAN)
            urllib.urlretrieve(url, filename, reporthook=dl_progress_callback_cmd)
    return internal_download


BiiHookPaths = namedtuple('paths', ['blocks', 'cmake', 'build', 'bin', 'deps', 'lib'])


class BiiHook(object):

    def __init__(self, name, block_name, is_dep, filenames, unresolved, hive_disk_image, out,
                 env_folder):
        self.paths = BiiHookPaths(blocks=hive_disk_image.paths.blocks,
                                  cmake=hive_disk_image.paths.cmake,
                                  build=hive_disk_image.paths.build,
                                  bin=hive_disk_image.paths.bin,
                                  deps=hive_disk_image.paths.deps,
                                  lib=hive_disk_image.paths.lib)
        self.name = name
        self.project_folder = hive_disk_image.paths.project_root
        self.block = block_name
        self.is_dependency = is_dep
        if is_dep:
            self.block_folder = os.path.join(hive_disk_image.paths.deps, block_name)
        else:
            self.block_folder = os.path.join(hive_disk_image.paths.blocks, block_name)
        self.settings = hive_disk_image.settings
        self.out = out
        self.download = _download(out)
        self.decompress = decompress
        self.files = filenames
        self.unresolved = unresolved
        self.environment_folder = env_folder

        # Some hooks use CMake, add it
        cmake_file_path = hive_disk_image.paths.cmake_path_file
        if os.path.exists(cmake_file_path):
            with open(cmake_file_path, "r") as f:
                cmake_path = f.read().strip()
                os.environ["PATH"] += os.pathsep + cmake_path

    def _paths_represent(self):
        return '\n'.join(["    bii.paths.blocks: %s" % self.paths.blocks,
                          "    bii.paths.cmake: %s" % self.paths.cmake,
                          "    bii.paths.build: %s" % self.paths.build,
                          "    bii.paths.bin: %s" % self.paths.bin,
                          "    bii.paths.deps: %s" % self.paths.deps,
                          "    bii.paths.lib: %s" % self.paths.lib])

    def __repr__(self):
        return '\n'.join(["bii.project_folder: %s" % self.project_folder,
                          "bii.block: %s" % self.block,
                          "bii.is_dependency: %s" % self.is_dependency,
                          "bii.block_folder: %s" % self.block_folder,
                          "bii.environment_folder: %s" % self.environment_folder,
                          "bii.paths:\n%s" % self._paths_represent(),
                          "bii.settings: %s" % self.settings,
                          "bii.files: %s" % self.files,
                          "bii.unresolved: %s" % self.unresolved])

    def execute(self, code):
        aux = {'bii': self}
        try:
            exec code in aux
        except Exception as e:
            self.out.error("processing hook: %s" % self.name)
            self.out.error("%s" % e)


def handle_hooks(stage, hive_holder, closure, bii):
    """ will manage user defined hooks. It has a problem, it works only if
    project is processed. So for clean, it has to detect if there are hooks,
    then execute a work first
    """
    hook_pattern = "bii*%s*hook.py" % stage

    #hooks must be executed also in order
    levels = hive_holder.hive_dependencies.version_graph.get_levels()
    list_blocks = [bv.block_name for level in levels for bv in level]
    _process_deps_hooks(closure, bii, hook_pattern, list_blocks)
    _process_blocks_hooks(hive_holder, bii, hook_pattern, list_blocks)


def _process_blocks_hooks(hive_holder, bii, hook_pattern, list_blocks):
    for block_name in list_blocks:
        try:
            block_holder = hive_holder[block_name]
        except KeyError:
            pass
        else:
            file_names = block_holder.cell_names
            for resource in block_holder.simple_resources:
                name = resource.name
                if fnmatch.fnmatch(name.cell_name, hook_pattern):
                    code = resource.content.load.load
                    unresolved = block_holder.unresolved()
                    hook = BiiHook(name, block_holder.block_name, False, file_names, unresolved,
                                   bii.hive_disk_image, bii.user_io.out,
                                   bii.bii_paths.user_bii_home)
                    hook.execute(code)


def _process_deps_hooks(closure, bii, hook_pattern, list_blocks):
    if closure is not None:
        files = compute_deps_files(closure)
        block_files = defaultdict(list)
        for bcn in files:
            block_files[bcn.block_name].append(bcn.cell_name)

        for block_name in list_blocks:
            try:
                bfiles = block_files[block_name]
            except KeyError:
                pass
            else:
                for name in bfiles:
                    if fnmatch.fnmatch(name, hook_pattern):
                        code = files[block_name + name]
                        unresolved = []  # FIXME, need to correctly compute unresolved here
                        hook = BiiHook(name, block_name, True, bfiles, unresolved,
                                       bii.hive_disk_image, bii.user_io.out,
                                       bii.bii_paths.user_bii_home)
                        hook.execute(code)
