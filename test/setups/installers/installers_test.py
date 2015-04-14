import unittest
from biicode.client.shell.userio import UserIO
from mock import Mock, patch
from biicode.client.exception import ClientException
from biicode.common.settings.osinfo import OSInfo
from biicode.client.setups.rpi_cross_compiler import install_gnu_arm



def mock_find(*args):
    if mock_find.called == 0:
        mock_find.called = +1
        return (None, None)
    else:
        return ('/usr/bin/gcc', '/usr/bin/gcc')
mock_find.called = 0

def mock_download(*args):
    return 'downloaded_file'

class CollaboratorInstallerTest(unittest.TestCase):
    '''Test that installers correctly calls collaborator, for specific collaborator tests check
    other files in this folder
    '''

    @patch.object(OSInfo, 'is_linux')
    def test_install_gnu_arm_non_linux(self, os_info):
        os_info.return_value = False
        ui = Mock(UserIO)
        with self.assertRaises(ClientException):
            install_gnu_arm(ui)

    @patch.object(OSInfo, 'is_linux')
    @patch('biicode.client.setups.rpi_cross_compiler.find_gnu_arm')
    @patch('biicode.client.setups.rpi_cross_compiler.download')
    @patch('biicode.client.setups.rpi_cross_compiler.install_linux_x32_compatibility')
    def test_install_gnu_arm_already_installed(self, lin32, download, finder, os_info):
        ui = Mock(UserIO)
        os_info.return_value = True
        finder.return_value = ('/usr/bin/gcc', '/usr/bin/gcc')
        install_gnu_arm(ui)
        self.assertFalse(download.called)
    
    @patch.object(OSInfo, 'is_linux')
    @patch('biicode.client.setups.rpi_cross_compiler.find_gnu_arm', side_effect=mock_find)
    @patch('biicode.client.setups.rpi_cross_compiler.download')
    @patch('biicode.client.setups.rpi_cross_compiler.decompress')
    @patch('biicode.client.setups.rpi_cross_compiler.install_linux_x32_compatibility')
    @patch('os.mkdir')
    def test_install_gnu_arm(self, mkdir, lin32, mock_decompress, mock_download, finder, os_info):
        ui = Mock(UserIO)
        os_info.return_value = True
        mock_download.return_value = 'downloaded_file'
        self.assertEqual(('/usr/bin/gcc', '/usr/bin/gcc'), install_gnu_arm(ui))
        self.assertTrue(mock_download.called)
        self.assertTrue(mock_decompress.called)
        self.assertTrue(lin32.called)
