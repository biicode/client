import inspect
from biicode.client.shell.biistream import Color


class ToolCatalog(dict):
    def __init__(self, main_class, tools):
        dict.__init__(self)
        self.main_class = main_class
        # dict from tool group name to set of classes
        for c in tools:
            self[c.group] = c
        self.show_advanced = False

    def _get_doc_short(self, doc):
        return doc.split('\n', 1)[0]

    def print_help(self, out, argv):
        out.writeln('\nSYNOPSIS:', Color.YELLOW)
        out.writeln('    $ bii COMMAND [options]')
        out.writeln('For help about a command:', Color.YELLOW)
        out.writeln('    $ bii COMMAND --help')
        out.write('To change verbosity, use options ', Color.YELLOW)
        out.writeln('--quiet --verbose\n')

        if not argv or 'all' in argv:
            out.writeln('--------- Global Commands ----------', Color.YELLOW)
            for m in inspect.getmembers(self.main_class, predicate=inspect.ismethod):
                method_name = m[0]
                if not method_name.startswith('_'):
                    method = m[1]
                    if not method.__doc__.startswith(' ADVANCED'):
                        doc = method.__doc__
                        out.write('  %-10s' % method_name, Color.GREEN)
                        out.writeln(self._get_doc_short(doc))
                    elif self.show_advanced:
                        doc = method.__doc__.replace(' ADVANCED', '')
                        out.write('  %-10s' % method_name, Color.GREEN)
                        out.writeln(self._get_doc_short(doc))

        if not argv:
            out.writeln('\n--------- Tools ----------', Color.YELLOW)
            out.writeln('For help about one or more tools ("all" for all):', Color.YELLOW)
            out.writeln('    $ bii --help TOOL [TOOL2]\n')
            for group, class_ in self.iteritems():
                out.write('  %-10s ' % class_.group, Color.GREEN)
                out.writeln(class_.__doc__)
        else:
            # Tools, as main commands
            for group, class_ in self.iteritems():
                if group not in argv and 'all' not in argv:
                    continue
                out.writeln('---------%s--------' % class_.__doc__, Color.YELLOW)
                for m in inspect.getmembers(class_, predicate=inspect.ismethod):
                    method_name = m[0]
                    method = m[1]
                    if method.__doc__:
                        method_doc = self._get_doc_short(method.__doc__)
                        if not method_name.startswith('_') and not method_doc.startswith('HIDDEN'):
                            com = '%s:%s' % (group, method_name)
                            out.write('  %-15s ' % com, Color.GREEN)
                            out.writeln(method_doc)
