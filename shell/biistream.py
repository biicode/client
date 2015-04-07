from biicode.common.output_stream import OutputStream, Color


class BiiOutputStream(OutputStream):
    '''Wraps an output stream, it can be constructed with sys.stdout,
    StringIO, cStringIO or any other file implementing class
    '''

    def success(self, data):
        self.writeln(data, Color.GREEN)

    def input_text(self, data):
        self.write(data, Color.GREEN)

    def header(self, data):
        self.writeln(data, Color.CYAN)

    def listitem(self, data, level=0):
        if level == 0:
            color = Color.CYAN
        elif level == 1:
            color = Color.BRIGHT_BLUE
        else:
            color = None
        self.writeln('  ' * level + str(data), color)

    def diff(self, data):
        ''' Print a textual diff '''
        lines = data.split("\n")
        for line in lines:
            if line.startswith("---") or line.startswith("+++") or not line:
                continue
            elif line.startswith("@@") and line.endswith("@@"):
                color = Color.CYAN
            elif line.startswith("-"):
                color = Color.RED
            elif line.startswith("+"):
                color = Color.GREEN
            else:
                color = None
            self.writeln(line, color)
