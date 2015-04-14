import os
from biicode.client.exception import ClientException
from biicode.common.utils.bii_logging import logger
from biicode.common.exception import BiiException
from biicode.client.command.process_executor import simple_exe
import sys
from biicode.common.settings.osinfo import OSInfo
from biicode.client.workspace.bii_paths import BiiPaths


class Arduino(object):
    def __init__(self, bii, hive_disk_image):
        self.bii = bii
        self.hive_disk_image = hive_disk_image

    def upload(self, possible_firmwares):
        '''Uploading the firmware to Arduino'''
        firmware = _firmware_to_upload(self.bii, possible_firmwares)
        self.bii.user_io.out.writeln('Uploading...')

        build_command = 'make' if sys.platform != 'win32' else 'mingw32-make'
        if OSInfo.is_linux():
            build_command = "sudo %s" % build_command
        build_command = "%s %s-upload" % (build_command, firmware)
        self._execute_upload_command(build_command)

    def ssh_upload(self, possible_firmwares, ip):
        '''Uploading the firmware to Arduino'''
        firmware = _firmware_to_upload(self.bii, possible_firmwares)
        self.bii.user_io.out.writeln('Uploading...')
        if not OSInfo.is_win():
            scp_command = "scp %s.hex root@%s:/tmp/" % (firmware, ip)
            ssh_command = "ssh root@%s /usr/bin/run-avrdude /tmp/%s.hex -q -q" % (ip, firmware)
            bii_paths = self.bii.bii_paths
            self._execute_command(scp_command, bii_paths.bin)
            self._execute_command(ssh_command)

    def _execute_command(self, command, cwd=None):
        retcode = simple_exe(command, cwd=cwd)
        if retcode != 0:
            raise BiiException('Upload failed')

    def _execute_upload_command(self, build_command):
        bii_paths = self.bii.bii_paths
        self._execute_command(build_command, bii_paths.build)

    def refresh_port(self):
        ''' Refresh port to check a new connection o reset it
            in case of leonardo board
        '''
        from biicode.client.dev.hardware.arduino.arduino_port_utils import refresh_port
        settings = self.hive_disk_image.settings
        arduino_settings = settings.arduino
        if not arduino_settings:
            raise BiiException('No arduino settings, please execute '
                               '"bii arduino:settings" first')
        port = refresh_port(self.bii.user_io,
                            arduino_settings.port,
                            reset=arduino_settings.automatic_reset)
        arduino_settings.port = port
        self.hive_disk_image.settings = settings
        return port


def _firmware_to_upload(bii, firmware_name=None):
    '''return the list of firmwares to upload in it'''
    bii_paths = bii.bii_paths
    firmwares_created = [f.split('.hex')[0] for f in os.listdir(bii_paths.bin)
                         if f.endswith("hex")]
    logger.debug('Firmwares created: %s' % str(firmwares_created))

    def _check_firmware_name(firmware_name, firmwares_created):
        for firmware in firmwares_created:
            if firmware_name == '':
                break
            if firmware_name == firmware:
                return firmware
            elif firmware_name in firmware:
                return firmware
        raise ClientException('Not a valid firmware name')

    if firmwares_created:
        if len(firmwares_created) > 1:
            if firmware_name:
                return _check_firmware_name(firmware_name, firmwares_created)
            bii.user_io.out.listitem('You have the following firmwares: ')
            for firmware in sorted(firmwares_created):
                bii.user_io.out.listitem(firmware, 1)
        else:
            return firmwares_created[0]
    else:
        raise ClientException('No firmware exists')
    firmware_name = bii.user_io.request_string('Firmware name')
    return _check_firmware_name(firmware_name, firmwares_created)
