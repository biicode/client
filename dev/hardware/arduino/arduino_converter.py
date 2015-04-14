from collections import defaultdict
import os
from biicode.common.settings.version import Version


'''
Module to create the cmake lines with the info of the boards.
It return the string that it is needed to compile and upload correctly the scketch to the Arduino.
This module is used always that biicode biicode create the arduino_settings.cmake.


=========> STEP 1: Read the board file and delete comment:

nano.name=Arduino Nano

nano.upload.tool=avrdude
nano.upload.protocol=arduino

## Arduino Nano w/ ATmega328
## -------------------------
nano.menu.cpu.atmega328=ATmega328
nano.menu.cpu.atmega328.upload.maximum_size=30720
nano.menu.cpu.atmega328.upload.maximum_data_size=2048

## Arduino Nano w/ ATmega168
## -------------------------
nano.menu.cpu.atmega168=ATmega168
nano.menu.cpu.atmega168.upload.maximum_size=14336
nano.menu.cpu.atmega168.upload.maximum_data_size=1024

-------------TO---------------

[("nano.name", "Arduino Nano"),
("nano.upload.tool", "avrdude"),
("nano.upload.protocol", "arduino"),
("nano.menu.cpu.atmega328", "ATmega328"),
("nano.menu.cpu.atmega328.upload.maximum_size", "30720"),
("nano.menu.cpu.atmega328.upload.maximum_data_size", "2048"),
("nano.menu.cpu.atmega168", "ATmega168"),
("nano.menu.cpu.atmega168.upload.maximum_size", "14336"),
("nano.menu.cpu.atmega168.upload.maximum_data_size", "1024")]

=========> STEP 2: Looking for the board settings and the list of the boards that share settings:

boards = {'nano': [[["nano", "name"], "Arduino Nano"],
                   [["nano", "upload", "tool"], "avrdude"],
                   [["nano", "upload", "protocol"], "arduino"]],

          'nano328': [[["nano328"], "ATmega328"],
                     [["nano328", "upload", "maximum_size"], "30720"],
                     [["nano328", "upload", "maximum_data_size"], "2048"]],

          'nano168': [[["nano168"], "ATmega168"],
                     [["nano168", "upload", "maximum_size"], "14336"],
                     [["nano168", "upload", "maximum_data_size"], "1024"]],
         }

partial_settings_board = set('nano328', 'nano168')

=========> STEP3: Convert the Arduino standard settings to Arduino Biicode settings

boards = {'nano328': [[["nano328", "name"], "Arduino Nano"],
                     [["nano328", "upload", "tool"], "avrdude"],
                     [["nano328", "upload", "protocol"], "arduino"],
                     [["nano328"], "ATmega328"],
                     [["nano328", "upload", "maximum_size"], "30720"],
                     [["nano328", "upload", "maximum_data_size"], "2048"]],

          'nano168': [[["nano168", "name"], "Arduino Nano"],
                     [["nano168", "upload", "tool"], "avrdude"],
                     [["nano168", "upload", "protocol"], "arduino"],
                     [["nano168"], "ATmega168"],
                     [["nano168", "upload", "maximum_size"], "14336"],
                     [["nano168", "upload", "maximum_data_size"], "1024"]],
         }

=========> STEP4: Create the partial Cmake with the settings info

#------------nano168------------
set(nano168.name "Arduino Nano")
set(nano168.upload.tool "avrdude")
set(nano168.upload.protocol "arduino")
set(nano168 "ATmega168")
set(nano168.upload.maximum_size "14336")
set(nano168.upload.maximum_data_size "1024")
set(nano168 SETTINGS upload name)
set(nano168.upload SUBSETTINGS maximum_size maximum_data_size tool protocol)

#------------nano328------------
set(nano328.name "Arduino Nano")
set(nano328.upload.tool "avrdude")
set(nano328.upload.protocol "arduino")
set(nano328 "ATmega168")
set(nano328.upload.maximum_size "30720")
set(nano328.upload.maximum_data_size "2048")
set(nano328 SETTINGS upload name)
set(nano328.upload SUBSETTINGS maximum_size maximum_data_size tool protocol)
'''


def cmake_board_settings(sdk_path, version):
    # Convert the Arduino standard settings to Arduino Biicode settings
    pretty_settings = boards_pretty_settings(sdk_path, version)
    # Create the partial Cmake with the settings info and return it
    return _settings_to_cmake(pretty_settings)


def _read_boards_file(sdk_path, version):
    board_path = os.path.join(sdk_path, 'hardware', 'arduino')
    if Version(version) >= Version('1.5'):
        board_path = os.path.join(board_path, 'avr', 'boards.txt')
    else:
        board_path = os.path.join(board_path, 'boards.txt')

    try:
        with open(board_path, 'rb') as f:
            content = f.readlines()
    except:
        content = ""
    content = [line.replace('\n', '').split('=') for line in content
                                                 if not(line.startswith('#') or line == "\n")]
    return content


def _settings_to_dict(content):
    partial_settings_board = set()
    boards = defaultdict(list)
    for setting, value in content:
        setting = setting.split('.')
        setting_name = setting[0]
        if 'menu' in setting and len(setting) > 3:
            setting_name = setting[0] + setting[3].replace('atmega', '')
            setting.remove(setting[3])
            setting.remove('menu')
            setting.remove('cpu')
            partial_settings_board.add(setting_name)
            setting[0] = setting_name

        boards[setting_name].append([setting, value])
    return boards, partial_settings_board


def boards_pretty_settings(sdk_path, version):
    # read board file and return a list with all the lines with info
    content = _read_boards_file(sdk_path, version)
    # Looking for the board settings and the list of the boards that share settings
    boards, partial_settings_board = _settings_to_dict(content)

    main_boards = set()
    for name in boards.keys():
        # looking for the boards which have some setting equal
        subboards = [ref for ref in partial_settings_board if ref.startswith(name) and name != ref]
        for subboard in subboards:
            for setting_components, value in boards[name]:
                # Change first component of the settings for the name of the board subfamily
                setting = [subboard]
                setting.extend(setting_components[1:])
                setting = [setting, value]
                # Update the settings with the new components
                boards[subboard].append(setting)
            main_boards.add(name)
    for name in main_boards:
        boards.pop(name)
    return boards


def _settings_to_cmake(boards):
    cmake_boards = []
    for name, settings in boards.iteritems():
        cmake_boards.append('\n#------------%s------------\n' % name)
        cmake_subsettings = defaultdict(list)
        cmake_settings = set()
        for setting_components, value in settings:
            cmake_boards.append('set(%s)\n' % ' '.join(('.'.join(setting_components),
                                                        '"%s"' % value)))
            if len(setting_components) == 3:
                _, _setting, _subsetting = setting_components
                cmake_subsettings[_setting].append(_subsetting)
            try:
                cmake_settings.add(setting_components[1])
            except IndexError:
                pass
        cmake_boards.append('set(%s SETTINGS %s)\n' % (name, ' '.join(cmake_settings)))
        for _key, _value in cmake_subsettings.iteritems():
            cmake_boards.append('set(%s SUBSETTINGS %s)\n' % ('.'.join((name, _key)),
                                                              ' '.join(_value)))
    return ''.join(cmake_boards)
