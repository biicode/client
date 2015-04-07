import sys
import platform
from biicode.common.exception import BiiException
from biicode.common.utils.bii_logging import logger
from serial import SerialException


def get_style():
    system = platform.system()
    if system == 'Darwin':
        return 'aqua'
    if system == 'Windows':
        return 'clam'
    return 'classic'


def monitor(toolchain, bii, port=None, baud_rate=9600):
    from Tkinter import (Tk, Text, RIGHT, Y, END, BOTH, N, S, E, W, Grid, Menu)
    from ttk import Style, Frame, Button, Scrollbar, Combobox
    from serial import Serial

    class Monitor(Frame):
        def __init__(self, parent, port, baud_rate, ser, toolchain, bii):
            '''
            Params:
                parent: The parent Frame
                port: string
                baud_rate:
                ser: serial
            '''

            Frame.__init__(self, parent)
            self.parent = parent
            self.port = port
            self.baud_rate = baud_rate
            self.ser = ser
            self.toolchain = toolchain
            self.bii = bii
            self.initUI()

        def initUI(self):
            self.parent.title("Biicode serial monitor %s" % self.port)
            self.style = Style()  # We need to define a style, otherwhise seems flat whit in macos
            self.style.theme_use(get_style())
            for x in range(1):
                Grid.columnconfigure(self, x, weight=1)
            for y in [1, 2]:
                Grid.rowconfigure(self, y, weight=1)

            self._make_top_bar()
            self._make_user_input()
            self._make_rcv_log()
            self._make_button_bar()

            self.pack(fill=BOTH, expand=1)

            self.serial_buffer = ""
            self.count = 0
            self.running = True
            self.after(50, self.read_serial)  # check serial again soon

        def _make_top_bar(self):
            menubar = Menu(self.parent)
            filemenu = Menu(menubar, tearoff=0)
            biimenu = Menu(menubar, tearoff=0)
            editmenu = Menu(menubar, tearoff=0)

            biimenu.add_command(label="Work (Save and process)", command=self.bii.work)
            biimenu.add_command(label="Find", command=self.bii.find)
            menubar.add_cascade(label="bii", menu=biimenu)

            filemenu.add_command(label="Flash code", command=self.upload)
            filemenu.add_separator()
            filemenu.add_command(label="Exit", command=self.parent.quit)
            menubar.add_cascade(label="File", menu=filemenu)

            editmenu.add_command(label="Clear", command=self.clear)
            # editmenu.add_separator()
            menubar.add_cascade(label="Edit", menu=editmenu)
            self.parent.config(menu=menubar)

        def _make_button_bar(self):
            self.button_upload = Button(self, text="Flash code", command=self.upload)
            self.button_upload.style = self.style
            self.button_upload.grid(row=0, column=0, padx=2, pady=2)

            self.baud_rate = 9600
            self.button_combobox = Combobox(self)
            self.button_combobox.bind("<<ComboboxSelected>>", self._update_baud_rate)
            bauds = (300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200)
            self.button_combobox['values'] = bauds
            self.button_combobox.current(4)
            self.button_combobox.grid(row=3, column=1, padx=2, pady=2)

        def _make_user_input(self):
            # make user input
            self.user_input = Text(self, width=52, height=3, takefocus=1,
                                   borderwidth=1, relief='ridge')
            self.user_input.grid(row=1, column=0, padx=2, pady=2, sticky=N + S + E + W)

            # make send button
            self.button_send = Button(self, text="Send", command=self.send_clicked)
            self.button_send.style = self.style
            self.button_send.grid(row=1, column=1, padx=2, pady=2, sticky=N + S + E + W)

        def _make_rcv_log(self):
            # make receive log
            recvLogFrame = Frame(self, width=400, height=200)
            recvLogFrame.style = self.style
            recvLogFrame.grid(row=2, column=0, padx=2, pady=2, sticky=N + S + E + W)
            self.start_stop_button = Button(self, text="Stop", command=self.start_stop_clicked)
            self.start_stop_button.style = self.style
            self.start_stop_button.grid(row=2, column=1, padx=2, pady=2, sticky=N + S + E + W)

            # make a scrollbar
            self.scrollbar = Scrollbar(recvLogFrame)
            self.scrollbar.pack(side=RIGHT, fill=Y)

            # make a text box to put the serial output
            self.log = Text(recvLogFrame, width=50, height=30, takefocus=0,
                            borderwidth=1, relief='ridge')
            self.log.pack(fill=BOTH, expand=True)

            # attach text box to scrollbar
            self.log.config(yscrollcommand=self.scrollbar.set)
            self.scrollbar.config(command=self.log.yview)

        def send_clicked(self):
            data = str(self.user_input.get(1.0, "end-1c") + '\0')
            self.ser.write(data)
            self._log(data)
            self.user_input.delete(1.0, END)

        def _log(self, msg):
            # if platform.system() == 'Darwin':
            #    print '>> %s' % msg
            # else:
            self.log.insert(END, '\n>> %s' % msg)
            self.log.yview(END)
            self.update_idletasks()

        def clear(self):
            self.log.delete(1.0, END)
            self.update_idletasks()

        def start_stop_clicked(self):
            if self.running:
                self.running = False
                self.start_stop_button['text'] = 'Start'
            else:
                self.running = True
                self.start_stop_button['text'] = 'Stop'
                self.read_serial()  # check serial again soon

        def upload(self):
            self.bii.work()
            try:
                if platform.system() == 'Darwin':
                    self.toolchain.upload()
                else:
                    self.ser.close()
                    self.toolchain.upload()
                    self.ser.open()
                self._log('** Code uploaded **')
            except BiiException:
                self._log('** Code upload failed **')

        def _update_baud_rate(self, event=None):
            new_rate = self.button_combobox.get()
            if new_rate != self.baud_rate:
                self.baud_rate = new_rate
                self.ser.setBaudrate(new_rate)
                logger.debug('Updated serial speed to %s' % new_rate)
                self.update_idletasks()

        def read_serial(self):
            self.log.update()  # display input text

            self._read_character()
            if self.running:
                self.after(100, self.read_serial)  # check serial again soon
            self.after(100, self.update_idletasks)

        def _read_character(self):
            try:
                c = self.ser.read()  # attempt to read a character from Serial
            except SerialException as e:
                logger.error("Couldn't read serial port: %s" % str(e))
                return

            # was anything read?
            while len(c) > 0 and c != '\r':
                # get the buffer from outside of this function
                # check if character is a delimeter
                if c == '\r':
                    c = ''  # don't want returns. chuck it
                if c == '\n':
                    # self.serial_buffer += "\n"  # add the newline to the buffer
                    self.log.insert(END, "\n")
                    self.log.insert(END, self.serial_buffer)
                    self.log.yview(END)
                    self.update_idletasks()
                    self.serial_buffer = ""  # empty the buffer
                else:
                    self.serial_buffer += c  # add to the buffer
                c = self.ser.read()

    # end Monitor class definition

    if port:
        ser = Serial(port, baud_rate, timeout=0, writeTimeout=0)  # ensure non-blocking
    else:
        raise BiiException("Unable to open monitor on undefined port")

    # make a TkInter Window
    sys.argv = ['']
    root = Tk()
    _ = Monitor(root, port, baud_rate, ser, toolchain, bii)
    root.mainloop()
