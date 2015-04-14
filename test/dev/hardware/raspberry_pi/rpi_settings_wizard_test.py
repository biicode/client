
import unittest
from biicode.common.settings.settings import Settings
from biicode.client.test.shell.user_io_mock import mock_user_io, mocked_user_io
from biicode.client.dev.hardware.raspberry_pi.rpi_settings_wizard import rpi_settings_wizard


class RaspberrySettingsWizardTest(unittest.TestCase):

    def test_no_ide(self):
        settings = Settings()
        user_io = mocked_user_io()
        mock_user_io(user_io, {'username': 'piuser',
                               'IP Address': '127.1.2.3',
                               'directory': 'mydir'})
        rpi_settings_wizard(user_io, settings)
        self.assertEqual(settings.rpi.directory, 'mydir')
        self.assertEqual(settings.rpi.ip, '127.1.2.3')
        self.assertEqual(settings.rpi.user, 'piuser')
