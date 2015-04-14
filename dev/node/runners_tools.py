from biicode.common.utils.file_utils import load_resource, save
from biicode.client.dev.node import DEV_NODE_DIR
import platform
import os
import stat


def create_noderunner(project_path, blocks_folder, deps_folder):
    if platform.system() == 'Windows':
        runner = "noderunner.bat"
    else:
        runner = "noderunner.sh"
    runners_template = load_resource(DEV_NODE_DIR, os.path.join("runners", runner))
    runner_path = os.path.join(project_path, runner)
    runner_content = runners_template.format(blocks_path=blocks_folder, deps_path=deps_folder)
    save(runner_path, runner_content)
    os.chmod(runner_path, stat.S_IRWXU)
