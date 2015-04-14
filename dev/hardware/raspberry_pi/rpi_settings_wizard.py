from biicode.client.shell.biistream import Color
from biicode.common.settings.cppsettings import CPPSettings
from biicode.common.settings.rpisettings import RPiSettings


def rpi_settings_wizard(user_io, settings):
    '''Configure Raspberry Pi settings
    param user_io: UserIO object
    param settings: existing hive Settings
    return: the new settings defined by the user
    '''
    if settings.rpi:
        user, ip, directory = settings.rpi.user, settings.rpi.ip, settings.rpi.directory
    else:
        user = "pi"
        ip = None
        directory = "bin"
    if  not settings.cpp:
        settings.cpp = CPPSettings()

    user_io.out.writeln('Define RPI settings for external C/C++ cross-building', front=Color.CYAN)
    user_io.out.writeln('If you are working on board the RPI, you don\'t need these settings',
                         front=Color.CYAN)

    settings.rpi.user = user_io.request_string('RPI username', user)
    settings.rpi.ip = user_io.request_ip('RPI IP Address', ip)
    settings.rpi.directory = user_io.request_string('RPI directory to upload', directory)


def rpi_settings_args(args, settings):
    if not settings.rpi:
        settings.rpi = RPiSettings()
    settings.rpi.user = args.user if args.user else settings.rpi.user
    settings.rpi.ip = args.ip if args.ip else settings.rpi.ip
    settings.rpi.directory = args.directory if args.directory \
                                            else settings.rpi.directory
    if  not settings.cpp:
        settings.cpp = CPPSettings()
