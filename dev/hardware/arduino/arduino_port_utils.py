import time
import serial
from serial.tools import list_ports
from biicode.common.settings.osinfo import OSInfo
from biicode.common.output_stream import Color
import platform


def _detect_arduino_port():
    """Returns a port configuration if founded due some common patterns"""
    port_patterns = {"Linux": ["arduino", "ttyACM", "ttyUSB"],
                     "Darwin": ["arduino", "usbmodem", "usbserial"],
                     "Windows": ["arduino"]}
    #. On Linux, it should be /dev/ttyACM0 or similar (for the Uno or Mega 2560)
    #  or /dev/ttyUSB0 or similar (for older boards).
    # On Windows, it will be a COM port but you'll need to check in the Device Manager
    # (under Ports) to see which one.
    # MAcos: /dev/tty.usbmodemXXX or /dev/tty.usbserialXXX for older ones
    found = []
    ports = [{"port": _port, "desc": _desc, "hwid": _hwid}
               for _port, _desc, _hwid in list_ports.comports()]
    for port in ports:
        for pattern in port_patterns[platform.system()]:
            if port["desc"] and pattern.lower() in port["desc"].lower() or \
               port["port"] and pattern.lower() in port["port"].lower():
                found.append(port["port"])
    return found


def check_port(user_io, current_port, wizard=False):
    '''detect and get the port the arduino is connected to
    param user_io: UserIO object
    param current_port: the current port, if any
    return: the actual port the arduino was found connected to
    '''
    # Search for arduino port
    port_list = _detect_arduino_port()
    if len(port_list) == 1:
        port = port_list[0]
        if current_port:
            if port != current_port:
                user_io.out.warn("The serial port has changed from %s => %s"
                                 % (current_port, port))
        current_port = port
    elif len(port_list) > 1:
        user_io.out.warn("There could be more than one arduino connected (%s)"
                         % (','.join(port_list)))
        if current_port and current_port not in port_list:
            user_io.out.warn("But your port %s is not among them" % current_port)
            port_list.append(current_port)
        if wizard:
            current_port = user_io.request_option('port',
                                                  default_option=current_port,
                                                  options=port_list,
                                                  one_line_options=True)
        else:
            user_io.out.warn("You might want to run arduino:settings to change it")
    elif len(port_list) == 0:
        user_io.out.error("We can't find an arduino connected")
        if wizard:
            current_port = user_io.request_string('Select port')
        else:
            user_io.out.warn("You might want to run arduino:settings to define port")

    current_port = current_port or 'None'
    user_io.out.writeln("Using arduino port: %s" % current_port, front=Color.GREEN)
    return current_port


def refresh_port(user_io, old_port, reset=False, wizard=False):
    ''' Refresh port to check a new connection o reset it
        in case of leonardo board
    '''
    # Check if port is detected
    # we have to distinct between leonardo and the others boards
    new_port = check_port(user_io, old_port, wizard)
    if reset:
        new_port = _reset_serial(user_io.out, new_port, wait_for_upload_port=True)
    return new_port


def get_boards_need_reset(sdk_path, arduino_sdk_version):
    '''Checking bootloader.file settings to analyze
       if it's needed to reset port. Pattern to find it, e.g.:
           LilyPadUSB.bootloader.file=Caterina-LilyPadUSB.hex (SDK vers < 1.5.x)
           LilyPadUSB.bootloader.file=caterina/Caterina-LilyPadUSB.hex (SDK vers == 1.5.x)

        parameters:
            sdk_path: Arduino SDK path
            arduino_sdk_version: Arduino SDK compatible version
        return:
            List of boards that user's SDK needs to be reseted before uploading
    '''
    from biicode.client.dev.hardware.arduino.arduino_converter import boards_pretty_settings
    board_settings = boards_pretty_settings(sdk_path, arduino_sdk_version)
    boards_need_reset = []
    for board, value in board_settings.iteritems():
        for _setting, _value in value:
            if 'file' in _setting and 'caterina' in _value.lower():
                boards_need_reset.append(board)
    return boards_need_reset


def _touch_serial_port(serial_port, baudrate=1200):
    ''' Reset current serial port with a given baudrate'''
    current_serial = serial.Serial()
    current_serial.port = serial_port
    current_serial.baudrate = baudrate
    current_serial.bytesize = serial.EIGHTBITS
    current_serial.stopbits = serial.STOPBITS_ONE
    current_serial.parity = serial.PARITY_NONE
    current_serial.open()
    current_serial.close()


def _reset_serial(out, serial_port, wait_for_upload_port=False):
    ''' Code original from https://github.com/Robot-Will/Stino/tree/master/app
        adapted to biicode to reset Arduino ports

        Reset any serial port.
            parameters:
                out: bii.user_io.out
                serial_port: current serial port detected
                wait_for_upload_port: True if board == 'leonardo'
            return:
                selected port
    '''
    caterina_serial_port = ''
    before_serial_list = _detect_arduino_port()
    if serial_port in before_serial_list:
        non_serial_list = before_serial_list[:]
        non_serial_list.remove(serial_port)

        out.success('Forcing reset using 1200bps open/close on port %s' % serial_port)
        _touch_serial_port(serial_port, 1200)

        if not wait_for_upload_port:
            time.sleep(0.4)
            return serial_port

        # Scanning for available ports seems to open the port or
        # otherwise assert DTR, which would cancel the WDT reset if
        # it happened within 250 ms. So we wait until the reset should
        # have already occurred before we start scanning.
        time.sleep(3 if OSInfo.is_win() else 0.3)

        # Wait for a port to appear on the list
        elapsed = 0
        while (elapsed < 10000):
            now_serial_list = _detect_arduino_port()
            diff_serial_list = [v for v in now_serial_list if v not in non_serial_list]

            out.success('Ports {%s}/{%s} => {%s}'
                                % (before_serial_list, now_serial_list, diff_serial_list))
            if len(diff_serial_list) > 0:
                caterina_serial_port = diff_serial_list[0]
                out.success('Found new upload port: %s' % caterina_serial_port)
                break

            # Keep track of port that disappears
            # before_serial_list = now_serial_list
            time.sleep(0.25)
            elapsed += 250

            # On Windows, it can take a long time for the port to disappear and
            # come back, so use a longer time out before assuming that the selected
            # port is the bootloader (not the sketch).
            if (((not OSInfo.is_win() and elapsed >= 500)
                or elapsed >= 5000) and (serial_port in now_serial_list)):
                out.success('Uploading using selected port: %s' % serial_port)
                caterina_serial_port = serial_port
                break

        if not caterina_serial_port:
            out.error("Couldn't find a Leonardo on the selected port. "
                      "Check that you have the correct port selected. "
                      "If it is correct, try pressing the board's reset"
                      " button after initiating the upload.")
    return caterina_serial_port or 'None'
