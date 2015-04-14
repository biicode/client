'''
Execute external process without user input
It handles very long outputs on different platforms

Prints output both to stdout and a variable to return
'''

from biicode.common.exception import BiiException
import os
from subprocess import PIPE, Popen, STDOUT
import platform
import select
import time
from biicode.client.shell.userio import UserIO


def simple_exe(command, cwd=None):
    # If there is testing output, capture and append to it
    if hasattr(simple_exe, 'output'):
        retcode, output = execute(command, cwd=cwd)
        simple_exe.output += output
        return retcode

    current_dir = os.getcwd()
    if cwd:
        os.chdir(cwd)
    try:
        retcode = os.system(command)
    finally:
        os.chdir(current_dir)
    return retcode


def execute(command, ui=None, cwd=None, env=None, shell=None):
    ex = {'Darwin': execute_mac,
          'Windows': execute_win,
          'Linux': execute_linux}
    if env is None:
        env = os.environ
    try:
        #TODO: Check this, the default is different in Windows and others
        if shell is None:
            if platform.system() == 'Windows':
                shell = False
            else:
                shell = True
        if ui is None:
            ui = UserIO()
        return ex[platform.system()](command, ui, cwd, env, shell)
    except KeyError:
        raise BiiException('Platform not supported')

MAX_OUPUT_SIZE = 1048576  # 1MB
import sys


def execute_mac(command, ui, cwd, env, shell):
    '''Spaws a process to execute given command'''
    import errno

    master_fd, slave_fd = os.pipe()
    if not env:
        env = {}
    path = os.getenv('PATH')
    for p in ['/usr/bin/', '/opt/local/bin/', '/usr/local/bin/']:
        if not p in path:
            path += ':' + p
    env['PATH'] = path
    proc = Popen(command, shell=shell, stdout=slave_fd, stderr=slave_fd, cwd=cwd, env=env)
    timeout = 1
    stdout = []

    while proc.poll() is None:
        try:
            inputready, _, _ = select.select([master_fd, sys.stdin], [], [], timeout)
            if inputready:
                data = os.read(master_fd, MAX_OUPUT_SIZE)
                if data:
                    ui.out.write(data)
                    stdout.append(data)
                    ui.out.flush(truncate=False)
        except OSError, e:
            if e.errno != errno.EINTR:
                raise

    out, err = proc.communicate()
    os.close(slave_fd)  # can't do it sooner: it leads to errno.EIO error
    os.close(master_fd)
    if out:
        stdout.append(out)
        ui.out.write(out)
    if err:
        stdout.append(err)
        ui.out.write(err)
    return (proc.returncode, '\n'.join(stdout))


def execute_linux(command, ui, cwd, env, shell):
    '''Spaws a process to execute given command'''
    def non_blocking_read(fd):
        import fcntl
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return os.read(fd, MAX_OUPUT_SIZE)
        except:
            return ''

    master_fd, slave_fd = os.pipe()
    if not env:
        env = {}
    env['PATH'] = os.getenv('PATH') + ":/opt/local/bin/"
    proc = Popen(command, shell=shell,
                 stdout=slave_fd, stderr=slave_fd, cwd=cwd,
                 env=env)
    timeout = 1
    stdout = []

    while proc.poll() is None:
        time.sleep(.2)
        inputready, _, _ = select.select([master_fd, sys.stdin], [], [], timeout)
        if inputready:
            #data = os.read(master_fd, MAX_OUPUT_SIZE)
            data = non_blocking_read(master_fd)
            if data:
                ui.out.write(data)
                stdout.append(data)
                ui.out.flush(truncate=False)

    inputready, _, _ = select.select([master_fd, sys.stdin], [], [], timeout)
    if inputready:
        data = non_blocking_read(master_fd)
        if data:
            ui.out.write(data)
            stdout.append(data)
            ui.out.flush(truncate=False)
    out, err = proc.communicate()
    os.close(slave_fd)  # can't do it sooner: it leads to errno.EIO error
    os.close(master_fd)
    if out:
        stdout.append(out)
        ui.out.write(out)
        ui.out.flush(truncate=False)
    if err:
        stdout.append(err)
        ui.out.write(err)
    return (proc.returncode, '\n'.join(stdout))


def execute_win(command, ui, cwd, env, shell):
    '''Spaws a process to execute given command'''
    try:
        proc = Popen(command, bufsize=1, shell=shell,
                     stdout=PIPE, stderr=STDOUT, cwd=cwd, env=env)
    except OSError as e:
        kls = e.__class__
        raise kls('%s. While executing %s' % (str(e), command))

    output = []

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        output.append(line)
        ui.out.write(line)
    out, err = proc.communicate()

    if out:
        output.append(out)
        ui.out.write(out)
    if err:
        output.append(err)
        ui.out.error(err)
    output = ''.join(output)
    return (proc.returncode, output)
