from subprocess import Popen, PIPE
import os
from biicode.common.model.origin_info import OriginInfo
from biicode.common.exception import BiiException
from biicode.common.utils.bii_logging import logger


def _execute_command(path, command):
    try:
        process = Popen(command.split(" "), stdout=PIPE, stderr=PIPE, cwd=path)
        (output, _) = process.communicate()
        exit_code = process.wait()
        return exit_code, output
    except OSError:
        raise BiiException("%s command not found! make sure it is in PATH." % command.split(" ")[0])
    except Exception:
        raise BiiException("Can't get '%s' remote info" % command.split(" ")[0])


def _parse_remotes(ouput):
    '''
    origin    https://github.com/lasote/libuv-1.git (fetch)
    origin    https://github.com/lasote/libuv-1.git (push)
    source    https://github.com/libuv/libuv.git (fetch)
    source    https://github.com/libuv/libuv.git (push)
    '''
    ret = {}
    lines = ouput.split(os.linesep)
    for num_line, line in enumerate(lines):
        is_fetch = num_line % 2 == 0  # Keep only fetch remotes
        if is_fetch:
            chunks = line.replace("\t", " ").split(" ")
            if len(chunks) > 1:
                ret[chunks[0]] = chunks[1]
    return ret


def git_info(folder):
    info = {}

    # Check enabled
    status_ret, status_out = _execute_command(folder, "git status --porcelain")
    info["enabled"] = status_ret == 0
    if not info["enabled"]:
        return info

    # Check all commited
    info["all_commited"] = status_out == ""

    # Read branch
    ret, out = _execute_command(folder, "git rev-parse --abbrev-ref HEAD")
    info["branch"] = out.replace(os.linesep, "") if ret == 0 else None

    # Check all pushed
    ret, out = _execute_command(folder, "git log origin/%s..HEAD" % info["branch"])
    info["all_pushed"] = out == ""

    # Check commit
    ret, out = _execute_command(folder, "git rev-parse HEAD")
    info["commit"] = out.replace(os.linesep, "") if ret == 0 else None

    # Check tag
    if info["commit"]:
        ret, out = _execute_command(folder, "git tag --points-at %s" % info["commit"])
        info["tag"] = out.replace(os.linesep, "") if ret == 0 else None
    else:
        info["tag"] = None

    # Check origins
    ret, out = _execute_command(folder, "git remote -v")
    info["remotes"] = _parse_remotes(out) if out else {}

    return info


def detect_updated_origin(block_path):

    vcs_detectors = [git_info]  # Extend with SVN, Mercurial etc

    for detector in vcs_detectors:
        inf = detector(block_path)
        if(inf and inf["enabled"]):
            if "origin" in inf["remotes"]:
                remote = inf["remotes"]["origin"]
            elif inf["remotes"]:
                remote = inf["remotes"][inf["remotes"].keys()[0]]
            else:  # Not remote
                continue
            if inf["all_pushed"] and inf["all_commited"]:
                return OriginInfo(remote, inf["branch"], inf["tag"], inf["commit"])
            else:
                raise BiiException("Discarding '%s' origin. Pending changes "
                                   "not pushed!" % remote)

    raise BiiException("No VCS origins detected!")


'''
Get info from git repository.
Usage:
    info = git_info("/home/laso/bii_lasote/libuv/blocks/lasote/libuv")
    print info["enabled"]
    if(info["enabled"]):
        print info["all_commited"]
        print info["branch"]
        print info["all_pushed"]
        print info["commit"]
        print info["tag"]
        print info["remotes"]
'''

