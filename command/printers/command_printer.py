from biicode.common.utils import file_utils as fileUtils
from biicode.common.utils.bii_logging import logger

class Printer(object):
    def __init__(self, out_stream):
        """ The only parameter of the PRinter is an output stream. It is nonsense that a printer
        had access to the model or the factory
        """
        self.out = out_stream

    def print_find_result(self, find_result):
        logger.debug("FIND RESULT: %s" % str(find_result))
        if not find_result:
            return

        if find_result.resolved:
            self.out.success('Find resolved new dependencies:')
            for resolved in find_result.resolved:
                self.out.success('\t%s' % str(resolved))

        if find_result.unresolved:
            self.out.error('Find could not resolve:')
            for unresolved in find_result.unresolved:
                self.out.listitem('\t%s' % unresolved.name)

        if find_result.updated:
            self.out.success('Updated dependencies:')
            for dep in find_result.updated:
                self.out.success('\t%s\n' % str(dep))
