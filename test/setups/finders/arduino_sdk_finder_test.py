
from biicode.common.test.bii_test_case import BiiTestCase
import os
import shutil
import platform
from nose.plugins.attrib import attr
from biicode.client.setups.finders.arduino_sdk_finder import valid_arduino_sdk_version,\
    find_arduino_sdks, print_sdks
from biicode.client.shell.biistream import BiiOutputStream


@attr('arduino')
class ArduinoSDKFinderTest(BiiTestCase):

    def test_valid_arduino_sdk_version(self):
        sdk_folder = self.new_tmp_folder()
        if platform.system() == 'Darwin':
            sdk_folder = os.path.join(sdk_folder, "Arduino.app/Contents/Resources/Java")

        lib_folder = os.path.join(sdk_folder, "lib")
        os.makedirs(lib_folder)
        with open(os.path.join(lib_folder, "version.txt"), "w") as versiontxt:
            versiontxt.write("1.0.6")

        self.assertEquals("1.0.6", valid_arduino_sdk_version(sdk_folder))

        # Delete SDK
        shutil.rmtree(os.path.join(lib_folder))
        self.assertIsNone(valid_arduino_sdk_version(sdk_folder))

    def test_get_all_paths(self):
        sdks = find_arduino_sdks()
        output = BiiOutputStream()
        print_sdks(output, sdks)
        self.assert_in_output("version=1.0.6", output)
        self.assert_in_output("version=1.5.8", output)
