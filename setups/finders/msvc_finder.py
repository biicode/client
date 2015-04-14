'''
  Role:
    utility methods for finding the local installation and paths of Microsoft visual Studio tools

'''

import os


def command_with_vcvars(generator, folder, command):
    '''wraps a command into a windows .bat file that first declares environment
    variables. Necessary for NMake builds
    :param builder, supposed to be NMake'''
    vc_var_all = _get_vcvarsall(generator)
    tmpbatname = os.path.join(folder, "vcvars_command.bat")
    with open(tmpbatname, 'w') as tmpbat:
        tmpbat.write('call "%s"\n' % vc_var_all)
        tmpbat.write('call ' + command)
    return tmpbatname


def is64bitWindows():
    import _winreg
    try:
        hKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion")
        _winreg.QueryValueEx(hKey, "ProgramFilesDir (x86)")
        return True
    except EnvironmentError:
        return False
    finally:
        _winreg.CloseKey(hKey)


def _get_vcvarsall(generator):
    import _winreg

    '''gets the location for the vcvarsall to be run, to declare VisualC
    environment variables'''
    value = None

    if is64bitWindows():
        key_name = r'SOFTWARE\Wow6432Node\Microsoft\VisualStudio\SxS\VC7'
    else:
        key_name = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\SxS\VC7'

    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, key_name)
        if generator.startswith('Visual Studio 10'):
            value, _ = _winreg.QueryValueEx(key, '10.0')
        elif generator.startswith('Visual Studio 9'):
            value, _ = _winreg.QueryValueEx(key, '9.0')
        elif generator.startswith('Visual Studio 8'):
            value, _ = _winreg.QueryValueEx(key, '8.0')
        else:
            raise EnvironmentError('Cannot find vcvarsall.bat location for: '
                                   + generator)
        path = value + 'vcvarsall.bat'
        if not os.path.exists(path):
            raise EnvironmentError("'%s' not found.")
    except EnvironmentError:
        return None
    return path


def get_vc_path(version):
    'version have to be 8.0, or 9.0 or... anything .0'
    import _winreg
    value = None

    if is64bitWindows():
        key_name = r'SOFTWARE\Wow6432Node\Microsoft\VisualStudio\SxS\VC7'
    else:
        key_name = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\SxS\VC7'
    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, key_name)
        value, _ = _winreg.QueryValueEx(key, version)
    except EnvironmentError:
        return None

    return value

if __name__ == '__main__':
    print 'VC.PATH => %s' % get_vc_path("10.0")
    print 'VC.PATH bat => %s' % _get_vcvarsall('Visual Studio 10')
    print 'VC.PATH => %s' % get_vc_path("2008")
    print 'VC.PATH bat => %s' % _get_vcvarsall('Visual Studio 8')
