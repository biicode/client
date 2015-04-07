from biicode.common.utils import file_utils
import os
from biicode.client.workspace.bii_ignore import BiiIgnore
from biicode.common.model.brl.block_cell_name import BlockCellName
from biicode.common.exception import InvalidNameException
from biicode.client.workspace.bii_paths import (BII_DIR, BIN_DIR, BUILD_DIR, CMAKE_DIR, DEP_DIR,
                                                LIB_DIR, SRC_DIR)


def walk_anonymous_block(bii_paths, bii_ignore, biiout, block_name):
    base_path = bii_paths.project_root
    result = {}
    bii_ignores = {}  # {folder: current bii_ignore}

    dir_skip = [bii_paths.get_by_name(d)
                for d in [DEP_DIR, BII_DIR, BIN_DIR, BUILD_DIR, CMAKE_DIR, LIB_DIR, SRC_DIR]]

    for root, directories, files in os.walk(base_path, followlinks=True):
        relative_path = os.path.relpath(root, base_path)
        # Alert for directories with \ char in the name
        to_keep = []
        for dir_name in directories:
            if "\\" in dir_name:
                biiout.warn('Invalid character "\\" on \'%s\' directory!' % dir_name)
            full_dir = os.path.join(root, dir_name)
            if full_dir not in dir_skip:
                to_keep.append(dir_name)
        directories[:] = to_keep
        split_rel_path = relative_path.split(os.sep)
        subfolder = '/'.join(split_rel_path[2:])
        current_bii_ignore = _get_filters(bii_ignore, bii_ignores, root, files, subfolder)

        for file_name_ in files:
            #file_, _ = os.path.splitext(file_name_)
            _, tail = os.path.split(file_name_)  # Tail is filename without extension

            if "\\" in tail:
                biiout.warn("Invalid character \"\\\" on file '%s'. "
                            "This file will be ignored!" % file_name_)
                continue

            relative_name = os.path.normpath(os.path.join(relative_path, file_name_))
            try:
                cell_name = block_name + relative_name
            except InvalidNameException as e:
                name = relative_name.replace('\\', '/')
                ignored = current_bii_ignore.ignored(name)
                if not ignored:
                    biiout.warn('%s. This file will be ignored\n' % e.message)
            else:
                ignored = current_bii_ignore.ignored(cell_name.cell_name)
                if ignored:
                    continue

                full_path = os.path.join(root, file_name_)

                try:
                    with open(full_path, 'rb') as handle:
                        content = handle.read()
                    result[cell_name] = content
                except IOError as e:
                    biiout.warn('Error reading "{}" file. Skipping'.format(file_name_))
                    continue

    return result


def walk_bii_folder(folder, bii_ignore, biiout):
    """
    Parameters:
        folder: Absolute folder path
        ui: UserIO
        bii_ignore: Filefilter
    Returns:
        dict {BlockCellName:(bytes or str}, of accepted files.
    """

    result = {}
    bii_ignores = {}  # {folder: current bii_ignore}

    #FIXME: Output msgs to user
    for root, directories, files in os.walk(folder, followlinks=True):
        relative_path = os.path.relpath(root, folder)
        # Alert for directories with \ char in the name
        for dir_name in directories:
            if "\\" in dir_name:
                biiout.warn('Invalid character "\\" on \'%s\' directory!' % dir_name)

        #Discard all the files in the upper folders
        split_rel_path = relative_path.split(os.sep)
        not_in_block = len(split_rel_path) < 2
        if not_in_block:
            subfolder = None
            for file_name_ in files:
                full_path = os.path.join(root, file_name_)
                relative_name = os.path.relpath(full_path, folder).replace('\\', '/')
                ignored = bii_ignore.ignored(relative_name)
                if not ignored:
                    biiout.warn('%s is misplaced, you should place it inside blocks folder. '
                                 'It will be ignored\n' % relative_name)
            continue
        else:
            subfolder = '/'.join(split_rel_path[2:])
        current_bii_ignore = _get_filters(bii_ignore, bii_ignores, root, files, subfolder)

        for file_name_ in files:
            #file_, _ = os.path.splitext(file_name_)
            _, tail = os.path.split(file_name_)  # Tail is filename without extension

            if "\\" in tail:
                biiout.warn("Invalid character \"\\\" on file '%s'. "
                            "This file will be ignored!" % file_name_)
                continue

            full_path = os.path.join(root, file_name_)
            relative_name = os.path.join(relative_path, file_name_)
            try:
                cell_name = BlockCellName(relative_name)
            except InvalidNameException as e:
                try:
                    _, _, name = relative_name.replace('\\', '/').split('/', 2)
                    ignored = current_bii_ignore.ignored(name)
                except:
                    ignored = False
                if not ignored:
                    biiout.warn('%s. This file will be ignored\n' % e.message)
                continue

            ignored = current_bii_ignore.ignored(cell_name.cell_name)
            if ignored:
                continue

            try:
                with open(full_path, 'rb') as handle:
                    content = handle.read()
                    result[cell_name] = content
            except IOError:  # Crashes when try to read a dead symbolic link
                biiout.warn('Error reading "{}" file. Skipping'.format(file_name_))
                continue

    if not result and not folder.endswith('deps'):
        biiout.debug('No valid files found in %s' % folder)
    return result


def _get_filters(bii_ignore, bii_ignores, root, files, subfolder):
    #Now get the bii_ignore
    parent_dir = os.path.dirname(root)
    current_bii_ignore = bii_ignores.get(parent_dir, bii_ignore)
    if 'ignore.bii' in files:
        ignorebii_path = os.path.join(root, 'ignore.bii')
        ignorebii = file_utils.load(ignorebii_path)

        current_bii_ignore = current_bii_ignore + BiiIgnore.loads(ignorebii, subfolder)
    bii_ignores[root] = current_bii_ignore
    return current_bii_ignore
