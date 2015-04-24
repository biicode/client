from biicode.common.model.cells import SimpleCell, VirtualCell
from biicode.common.exception import ConfigurationFileError


def compute_files(hive_holder, output, settings):
    """ given the current hive_holder, compute the files that have to be saved in disk
    return: {BlockCellName: StrOrBytes to be saved in disk}
    param output: something that supports info, warn, error
    """
    new_files = {}

    for block_cell_name, (cell, content) in hive_holder.resources.iteritems():
        if isinstance(cell, VirtualCell):
            try:
                target = cell.evaluate(settings)
            except ConfigurationFileError as e:
                output.error("Error evaluating virtual %s: %s" % (block_cell_name, e.message))
                continue
            content = hive_holder[target.block_name][target.cell_name].content
            new_files[block_cell_name] = content.load.load
        elif content.blob_updated:
            new_files[block_cell_name] = content.load.load

    return new_files


def compute_deps_files(closure):
    """ in the closure, the settings have been already evaluated
    return: {BlockCellName: StrOrBytes to be saved in disk}
    """
    files = {}

    for block_cell_name, (resource, _) in closure.iteritems():
        if isinstance(resource.cell, SimpleCell):
            if resource.cell.container is None:
                files[block_cell_name] = resource.content.load.load
            else:
                files[resource.cell.container] = resource.content.load.load
    return files
