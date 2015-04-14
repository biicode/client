from biicode.client.command.process_executor import execute
from biicode.common.settings.version import Version
import re
from biicode.client.shell.biistream import BiiOutputStream
from biicode.client.shell.userio import UserIO


def gnu_version(compiler):
    try:
        _, output = execute('%s --version' % compiler, ui=UserIO(out=BiiOutputStream()))
        installed_version = re.search("[0-9]\.[0-9]\.[0-9]", output).group()
    except:
        installed_version = ''
    if installed_version:
        return Version(installed_version)
