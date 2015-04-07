from biicode.common.settings.arduinosettings import ArduinoSettings
from biicode.common.exception import BiiException
from biicode.client.setups.finders.arduino_sdk_finder import (valid_arduino_sdk_version,
                                                              find_arduino_sdks, print_sdks)
from biicode.client.dev.hardware.arduino.arduino_port_utils import refresh_port,\
    get_boards_need_reset


SDK_GALILEO = 'galileo'
SDK_BETA = '1.5.5'

Arduino_boards = ['uno', 'leonardo', 'yun', 'zum', 'atmega328', 'diecimila', 'nano328',
                  'nano', 'mega2560', 'mega', 'esplora', 'micro', 'mini328',
                  'mini', 'ethernet', 'fio', 'bt328', 'bt', 'LilyPadUSB', 'lilypad328',
                  'lilypad', 'pro5v328', 'pro5v', 'pro328', 'pro', 'atmega168',
                  'atmega8', 'robotControl', 'robotMotor'
                  ]

board_mapping = {'zum': 'bt328'}


def arduino_settings_args(user_io, args, settings):
    ''' Method to select (without any wizard) from command line your SDK,
        port, board and automatic reset.
        Port and SDK arguments support "default" option to make automatically
        the setting selection
    '''
    if settings.arduino is None:
        settings.arduino = ArduinoSettings()
    if not args.sdk and not settings.arduino.sdk:
        _, default_sdk = get_valid_sdks(user_io, settings.arduino)
        user_io.out.success("Your default SDK is: %s" % default_sdk)
        settings.arduino.sdk = default_sdk
    else:
        settings.arduino.sdk = args.sdk or settings.arduino.sdk
    try:
        valid_version = valid_arduino_sdk_version(settings.arduino.sdk)
    except:
        valid_version = None
    if not valid_version:
        raise BiiException("No valid Arduino SDK version could be found."
                           " Check if /your_SDK_path/lib/version.txt file exists")
    settings.arduino.version = valid_version
    if args.need_reset:
        settings.arduino.automatic_reset = True if args.need_reset == 'true' else None
    if (not args.port and not settings.arduino.port) or args.port == 'auto':
        settings.arduino.port = refresh_port(user_io,
                                             settings.arduino.port,
                                             reset=settings.arduino.automatic_reset,
                                             wizard=False)
    else:
        settings.arduino.port = args.port or settings.arduino.port
    settings.arduino.board = args.board or settings.arduino.board


def arduino_settings_wizard(user_io, settings):
    '''gets arduino settings from user. The port will always be scanned
       param user_io: UserIO object
       param settings: existing hive Settings
    '''

    if settings.arduino is None:
        settings.arduino = ArduinoSettings()

    _arduino_sdk_wizard(user_io, settings.arduino)
    _get_board(user_io, settings.arduino)
    ports_need_reset = get_boards_need_reset(settings.arduino.sdk, settings.arduino.version)
    settings.arduino.automatic_reset = True if settings.arduino.board in ports_need_reset \
                                            else None
    settings.arduino.port = refresh_port(user_io,
                                         settings.arduino.port,
                                         reset=settings.arduino.automatic_reset,
                                         wizard=True)


def _arduino_sdk_wizard(user_io, arduino_settings):
    ''' User'll set his Arduino SDK path or will select the
        auto-detection of the Arduino SDK path located in
        biicode_env folder.
    '''
    sdks, default_sdk = get_valid_sdks(user_io, arduino_settings)
    sdk_path = user_io.request_string("Enter SDK number or type path", default_sdk)
    sdk_path = sdk_path or default_sdk or "None"
    try:
        number = int(sdk_path)
    except ValueError:
        selected_sdk = sdk_path
        selected_version = valid_arduino_sdk_version(sdk_path, user_io.out)
        if not selected_version:
            user_io.out.error("SDK not valid: %s" % sdk_path)
            selected_version = "None"
    else:
        try:
            selected_sdk, selected_version = sdks[number]
        except IndexError:
            raise BiiException("Bad Index %d, please select number or type path" % number)

    arduino_settings.sdk = selected_sdk.replace('\\', '/')
    arduino_settings.version = selected_version


def get_valid_sdks(user_io, arduino_settings):
    sdks = find_arduino_sdks()
    if not sdks:
        user_io.out.warn("Biicode couldn't find a default Arduino SDK path")

    filtered_sdks = []
    for (sdk_path, version) in sdks:
        if " " in sdk_path:
            user_io.out.warn("Detected SDK(%s) in %s\nbut paths with spaces are not valid.\n"
                             "Please install it in another location" % (version, sdk_path))
        else:
            filtered_sdks.append((sdk_path, version))
    sdks = filtered_sdks

    print_sdks(user_io.out, sdks)

    if arduino_settings.sdk:
        default_sdk = arduino_settings.sdk
    else:
        default_sdk = None
        for path, version in sdks:
            if version == "1.0.6":
                default_sdk = path
                break
    return sdks, default_sdk


def _get_board(user_io, arduino_settings):
    boards = Arduino_boards
    boards.sort()
    while True:
        selected_board = user_io.request_string("Enter board (/o list supported options)",
                                                arduino_settings.board)
        if selected_board and selected_board != '/o':
            if selected_board not in boards:
                user_io.out.warn("The board, %s, isn't in current supported Arduino boards "
                                 "list options. Make sure you've all the necessary SW installed "
                                 "in your Arduino SDK version" % selected_board)
            arduino_settings.board = selected_board
            break

        user_io.print_options(options=boards)
