from biicode.common.utils.bii_logging import logger
from biicode.common.model.cells import VirtualCell, SimpleCell, Cell
from collections import defaultdict
from biicode.common.model.bii_type import BiiType


class MainInfo(object):
    def __init__(self, main_cell):
        self.main_cell = main_cell
        self.src = set()  # Sources, EXCLUDING the main cell
        self.data = set()
        self.system_includes = defaultdict(set)  # {BlockName: set of system includes}

    @property
    def main_name(self):
        """ return BlockCellName of main file
        """
        return self.main_cell.name

    @property
    def main_data(self):
        return self.main_cell.dependencies.data

    @property
    def main_system(self):
        return self.main_cell.dependencies.system


def compute_mains(settings, resources, output):
    """Return a dictionary {main_name: MainInfo} with all the information
    with all necessary resources to build these mains.
    """

    cells_with_main = [r.cell for r in resources.itervalues() if r.cell.hasMain]
    cells = {r.name: r.cell for r in resources.itervalues()}
    mains = {}

    for main_cell in cells_with_main:
        # filtering out headers
        if BiiType.isCppHeader(main_cell.name.extension):
            output.info("skipping main function in header file %s" % main_cell.name)
        mains[main_cell.name] = _compute_main_info(main_cell, cells, settings)

    return mains


def _compute_main_info(main_cell, cells, settings):
    '''Useful for computing the connected set of a certain resource
    (lets say, a C++ main)
    :param root: can be a SimpleCell or an iterable of SimpleCell.
    @return
    '''
    assert isinstance(main_cell, Cell)
    main_info = MainInfo(main_cell)
    open_set = set()
    if isinstance(main_cell, VirtualCell):
        id_ = main_cell.evaluate(settings)
        main_cell = cells[id_]
    assert isinstance(main_cell, SimpleCell)
    # Analyze this cell deps and data and system_deps
    for target in main_cell.dependencies.targets:
        if target in cells:
            open_set.add(cells[target])

    while open_set:
        cell = open_set.pop()
        main_info.src.add(cell.name)
        if isinstance(cell, VirtualCell):
            id_ = cell.evaluate(settings)
            cell = cells[id_]
        assert isinstance(cell, SimpleCell)
        # Analyze this cell deps and data and system_deps
        for target in cell.dependencies.targets:
            if target in cells and target not in main_info.src:
                open_set.add(cells[target])
        for target in cell.dependencies.data:
            if target in cells:
                main_info.data.add(target)
        main_info.system_includes[cell.name.block_name].update(cell.dependencies.system)

    # No transitivity yet in Data Resources

    excluded = main_cell.dependencies.exclude_from_build
    _collect_exclude_from_build(cells, main_info.src, excluded, settings)
    main_info.src = main_info.src - excluded
    logger.debug("Computed MainInfo: %s" % main_info)
    return main_info


def _collect_exclude_from_build(cells, cell_names, exclude_from_build, settings):
    """Exclude all dependencies that shouldn't be compiled.
       For example a Fortran module can depend on include, so,
       this included file mustn't be compiled."""
    for cell_name in cell_names:
        cell = cells[cell_name]
        if isinstance(cell, VirtualCell):
            id_ = cell.evaluate(settings)
            cell = cells[id_]
        exclude_from_build.update(cell.dependencies.exclude_from_build)
