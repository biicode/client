import unittest
from mock import MagicMock
from mock import patch
from biicode.client.shell.userio import UserIO
from biicode.client.dev.hardware.raspberry_pi.raspberrypi import RaspberryPi
from biicode.client.workspace.hive_disk_image import HiveDiskImage
from biicode.client.workspace.bii_paths import BiiPaths


@patch('biicode.client.dev.hardware.raspberry_pi.raspberrypi.execute')
class RaspberryPiUnitTests(unittest.TestCase):

    def setUp(self):
        # Mocks declarations
        self.hive_disk_image_mock = MagicMock(HiveDiskImage)
        paths_mock = MagicMock(BiiPaths)
        paths_mock.hive = ''
        self.io_mock = MagicMock(UserIO)
        self.paths = paths_mock

        # Settings RPi
        self.user = "lamport"
        self.ip = "127.0.0.23"
        self.hive_disk_image_mock.settings.rpi.user = self.user
        self.hive_disk_image_mock.settings.rpi.ip = self.ip

        self.cut = RaspberryPi(self.io_mock, paths_mock, self.hive_disk_image_mock)
