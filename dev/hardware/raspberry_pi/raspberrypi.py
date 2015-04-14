
import os
from biicode.client.exception import ClientException
from biicode.client.command.process_executor import execute


class RaspberryPi(object):
    '''General class with functions that are specific to the machine and not to the programming
    language'''
    def __init__(self, user_io, paths, hive_disk_image):
        self.user_io = user_io
        self.paths = paths
        self.hive_disk_image = hive_disk_image

    def sync_dinlib(self):
        """Synchronize Rpi OpenGLES shared libs to hive lib folder."""
        user, ip, _, _ = self._rpi_settings

        hive_lib_path = os.path.join(self.paths.hive, "lib")
        command = "rsync -chavzP {}@{}:'/opt/vc/lib/* /opt/vc/include' {}".format(user, ip,
                                                                                  hive_lib_path)

        rsync_status, _ = execute(command, self.user_io)
        if rsync_status:
            self.user_io.out.error("Cannot connect to RaspberryPi make sure that it is "
                                   "connected to the network.")

    @property
    def _rpi_settings(self):
        try:
            rpi = self.hive_disk_image.settings.rpi
            return rpi.user, rpi.ip, rpi.directory
        except Exception as e:
            raise ClientException('In your R-PI settings in settings.bii\n'
                                  'Error: %s\n'
                                  'You should fix the file, or run bii rpi:settings\n' % str(e))

    def send_sync(self):
        '''Send by rsync the bin folder into the specified directory.'''
        bin_dir = self.paths.bin
        user, ip, directory = self._rpi_settings
        rpi_directory = '%s/%s/' % (directory, self.paths.project_name)

        command = ('rsync -aq --rsync-path="mkdir -p ~/%s && rsync" -Pravdtze ssh %s/* %s@%s:%s'
                   % (rpi_directory, bin_dir, user, ip, rpi_directory))
        self.user_io.out.info('Sending with %s\n' % command)
        try:
            _, out = execute(command, self.user_io, cwd=bin_dir)
            if out:
                self.user_io.out.info("%s" % out)
        except Exception as e:
            raise ClientException('Sending bin folder\n'
                                  'ERROR: %s\n' % str(e))

    def ssh(self):
        user, ip, _ = self._rpi_settings

        command = ('ssh %s@%s' % (user, ip))
        self.user_io.out.info('Connecting with %s\n' % command)
        _, out = execute(command, self.user_io)
        self.user_io.out.info("%s" % out)
