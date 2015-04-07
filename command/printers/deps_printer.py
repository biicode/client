from biicode.common.output_stream import Color
from collections import defaultdict
from biicode.common.exception import BiiException
import fnmatch
from biicode.common.model.cells import SimpleCell


def print_deps(out, hive_holder, block_name=None, details=False, files=False):
    ''' Print the general block dependencies '''
    block_holders = {block.block_name: block for block in hive_holder.block_holders}
    # filter block_name
    if block_name is not None:
        try:
            block_holders = {block_name: block_holders[block_name]}
        except KeyError:
            raise BiiException("Block name '%s' not exists" % block_name)

    if files is not None:
        _print_deps_files(out, block_holders, files)
    else:
        _print_deps_details(out, block_holders, details)


def _print_deps_details(out, block_holders, details):
    if details is not None:
        show_details = True
        if not details:
            details = ['*']
    else:
        show_details = False

    def _show_origins():
        if show_details:
            for origin in sorted(origins):
                out.writeln("                %s" % str(origin))

    for block in sorted(block_holders):
        block_holder = block_holders[block]
        out.write(block, Color.BRIGHT_GREEN)
        out.writeln(" depends on:")

        dep_table = block_holder.requirements
        deps_dict = _deps(block_holder)

        for block_name in sorted(deps_dict):
            dict_cell_names = deps_dict[block_name]
            if block == block_name:
                block_version = "%s (self)" % block
                if not details:
                    continue
            else:
                block_version = dep_table.get(block_name, "Error, dep not found")
            out.writeln("       %s" % str(block_version), Color.BRIGHT_CYAN)
            for cell_name in sorted(dict_cell_names):
                if not _check_file_patterns(cell_name, details):
                    continue
                origins = dict_cell_names[cell_name]
                out.writeln("          %s" % cell_name, Color.CYAN)
                _show_origins()

        systems = _system(block_holder)
        unresolveds = _unresolved(block_holder)
        if systems:
            out.writeln("       system:", Color.BRIGHT_YELLOW)
            for system in sorted(systems):
                if not _check_file_patterns(system, details):
                    continue
                origins = systems[system]
                out.writeln("          %s" % system, Color.YELLOW)
                _show_origins()

        if unresolveds:
            out.writeln("       unresolved:", Color.BRIGHT_RED)
            for unresolved in sorted(unresolveds):
                if not _check_file_patterns(unresolved.name, details):
                    continue
                origins = unresolveds[unresolved]
                out.writeln("          %s" % unresolved, Color.RED)
                _show_origins()


def _unresolved(block_holder):
    unresolved = defaultdict(set)
    for cell, _ in block_holder.simple_resources:
        for unr in cell.dependencies.unresolved:
            unresolved[unr].add(cell.name.cell_name)
    return unresolved


def _system(block_holder):
    system = defaultdict(set)
    for cell, _ in block_holder.simple_resources:
        for s in cell.dependencies.system:
            system[s].add(cell.name.cell_name)
    return system


def _deps(block_holder):
    deps = defaultdict(lambda: defaultdict(set))
    for cell, _ in block_holder.simple_resources:
        for s in cell.dependencies.explicit:
            deps[s.block_name][s.cell_name].add("%s (E)" % cell.name.cell_name)
        for s in cell.dependencies.implicit:
            deps[s.block_name][s.cell_name].add("%s (I)" % cell.name.cell_name)
    return deps


def _check_file_patterns(name, patterns):
        if not patterns:
            return True
        for p in patterns:
            if fnmatch.fnmatch(name, p):
                return True
        return False


def _print_deps_files(out, block_holders, files):

    for block in sorted(block_holders):
        block_holder = block_holders[block]
        out.writeln(block, Color.BRIGHT_GREEN)
        cells = {cell.name.cell_name: cell for cell, _ in block_holder.resources.itervalues()}
        for cell_name in sorted(cells):
            if not _check_file_patterns(cell_name, files):
                continue
            cell = cells[cell_name]
            out.writeln("       %s [%s]%s"
                        % (cell_name, cell.type, '[M]' if cell.hasMain else ''),
                        Color.BRIGHT_CYAN)
            if isinstance(cell, SimpleCell):
                for s in sorted(cell.dependencies.explicit):
                    out.writeln("           %s (E)" % s)
                for s in sorted(cell.dependencies.implicit):
                    out.writeln("           %s (I)" % s)
                for s in sorted(cell.dependencies.system):
                    out.writeln("           %s (S)" % s, Color.YELLOW)
                for s in sorted(cell.dependencies.data):
                    out.writeln("           %s (D)" % s, Color.MAGENTA)
                for s in sorted(cell.dependencies.unresolved):
                    out.writeln("           %s (U)" % s, Color.RED)
            else:
                for s in sorted(cell.resource_leaves):
                    out.writeln("           %s (V)" % s.cell_name)
