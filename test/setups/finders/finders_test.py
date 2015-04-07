import unittest
from biicode.common.settings.version import Version
from mock import patch
from biicode.client.setups.finders.finders import gnu_version
from biicode.client.setups.rpi_cross_compiler import find_gnu_arm
from biicode.client.workspace.bii_paths import get_biicode_env_folder_path


GCC_VERSION_MAC = '''Configured with: --prefix=/Applications/Xcode.app/Contents/Developer/usr --with-gxx-include-dir=/usr/include/c++/4.2.1
Apple LLVM version 5.1 (clang-503.0.38) (based on LLVM 3.4svn)
Target: x86_64-apple-darwin13.1.0
Thread model: posix'''

GCC_VERSION_UBUNTU = '''gcc (Ubuntu/Linaro 4.8.1-10ubuntu9) 4.8.1
Copyright (C) 2013 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
'''

GCC_VERSION_WIN = '''gcc (GCC) 4.8.1
Copyright (C) 2013 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.'''


class FindersTest(unittest.TestCase):

    @patch('biicode.client.setups.finders.finders.execute')
    def test_gnu_version_detection(self, execute_mock):
        execute_mock.return_value = ("", GCC_VERSION_MAC)
        self.assertEquals(gnu_version('gnu'), Version('4.2.1'))
        execute_mock.return_value = ("", GCC_VERSION_UBUNTU)
        self.assertEquals(gnu_version('gnu'), Version('4.8.1'))
        execute_mock.return_value = ("", GCC_VERSION_WIN)
        self.assertEquals(gnu_version('gnu'), Version('4.8.1'))

    @patch('os.path.exists')
    def test_find_gnu_arm(self, exists):
        exists.return_value = False
        self.assertEqual((None, None), find_gnu_arm())

        exists.return_value = True
        c_path, cpp_path = find_gnu_arm()
        inst_path = get_biicode_env_folder_path().replace('\\', '/')
        c_path = c_path.replace('\\', '/')
        cpp_path = cpp_path.replace('\\', '/')
        inst_path = '%s/raspberry_cross_compilers/arm-bcm2708/'\
                    'arm-bcm2708hardfp-linux-gnueabi/bin/'\
                    'arm-bcm2708hardfp-linux-gnueabi' % inst_path
        self.assertTrue(cpp_path.endswith('%s-g++' % inst_path))
        self.assertTrue(c_path.endswith('%s-gcc' % inst_path))
