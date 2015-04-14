from biicode.common.exception import BiiException
from biicode.common.output_stream import Color
from biicode.common.diffmerge.compare import diff
from biicode.common.model.symbolic.block_version import BlockVersion


def print_diff(out, hive_holder, biiapi, block_name, first_version, second_version, short):
    if block_name:
        if block_name not in hive_holder.blocks:
            raise BiiException("Unkown block {}. Enter a valid block name.".format(block_name))
        parent = hive_holder[block_name].parent
        bv1 = BlockVersion(parent.block, first_version) if first_version is not None else None
        bv2 = BlockVersion(parent.block, second_version) if second_version is not None else None
        text_diff = diff(biiapi, hive_holder[block_name], bv1, bv2)
        bv1 = bv1 or parent
        bv2 = bv2 or parent
        _print_diff(out, text_diff, bv1, bv2, short)
    else:
        for block_name in sorted(hive_holder.blocks):
            #diff_builder = _diff_builder(hive_holder, biiapi, bversion_child)
            text_diff = diff(biiapi, hive_holder[block_name])
            bv1 = hive_holder[block_name].parent
            bv2 = BlockVersion(bv1.block, None)
            _print_diff(out, text_diff, bv1, bv2, short)


def _print_diff(out, diff, bversion_child, bversion_parent, short_message=False):
    if bversion_parent is None:
        bversion_parent = bversion_child
    out.writeln("diff '%s' '%s'" % (bversion_child.to_pretty(), bversion_parent.to_pretty()),
                Color.BRIGHT_GREEN)

    if not any([diff.created, diff.deleted, diff.modified, diff.renames]):
        out.header("No changes")

    for mode in ['deleted', 'created', 'modified']:
        _print_diff_file_mode(out, str(bversion_child.block_name), diff, mode, short_message)

    # renamed files
    for k, v in diff.renames.iteritems():
        out.header("renamed:   %s => %s" % (k, v))


def _print_diff_file_mode(out, bname, diff, mode, short_message=False):
    color_short_message = None
    header_msg = "{mode} file mode\n---a/{file}\n+++b/{file}"

    if mode is 'deleted':
        diff_mode = diff.deleted
        color_short_message = Color.RED
        header_msg = "{mode} file mode\n---a/{file}\n+++/dev/null"
    elif mode is 'created':
        diff_mode = diff.created
        color_short_message = Color.GREEN
    elif mode is 'modified':
        diff_mode = diff.modified
        color_short_message = Color.YELLOW

    for k, v in diff_mode.iteritems():
        diff_content = v[1]
        cell_name = '%s/%s' % (bname, k)
        if short_message:
            _print_diff_short_message(out, k, diff_content, mode, color_short_message)
        else:
            out.writeln(header_msg.format(file=cell_name, mode=mode), Color.BRIGHT_WHITE)
            out.diff(diff_content + "\n")


def _print_diff_short_message(out, file_name, diff_content, mode, header_color):
    additions, deletions = _get_additions_and_deletions(diff_content)
    out.write("%s:   %s  " % (mode, file_name), header_color)
    out.write("+%s" % additions, Color.BRIGHT_GREEN)
    out.writeln("-%s" % deletions, Color.BRIGHT_RED)


def _get_additions_and_deletions(content):
    ''' Return the number of added and deleted lines
        parameter:
              content: diff content. It has a line like this: @@ -0,0 +1,19 @@
    '''
    import re
    if not content:
        return '0', '0'
    total_additions = 0
    total_deletions = 0
    add_and_del = re.findall('@@ (.+?) @@', content)
    for _add_and_del in add_and_del:
        add_and_del = _add_and_del.split(' ')  # ["-4,5", "+2,45"]
        additions = add_and_del[1].split('+')[1]
        deletions = add_and_del[0].split('-')[1]
        if ',' in additions:
            total_additions += int(additions.split(',')[1])
        if ',' in deletions:
            total_deletions += int(deletions.split(',')[1])
    return total_additions, total_deletions
