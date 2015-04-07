
import fnmatch
from biicode.common.exception import BiiException


default_bii_ignore = '''
# You can edit this file to add accepted and ignored file extensions
# The format is similar to gitignore files.
# Rules are evaluated in order.
#
# Format is as follows:
#    <pattern>
# pattern: conforms Unix Filename Pattern Matching, if preceded by ! it is negated, thus accepts
#            instead of ignoring (previously ignored by a precedent rule)
#

# Compiled source #
*.com
*.class
*.dll
*.exe
*.o
*.so
*.obj
*.pyc
*.dir

# Editor backups
*~

# Hidden files
.*
*/.*

# OS generated files
Thumbs.db
ehthumbs.db
.DS_STORE
'''


class BiiIgnore(list):
    ''' a list of rules, each one tuple (patter, accept)'''
    def __add__(self, other):
        result = BiiIgnore()
        result.extend(self)
        result.extend(other)
        return result

    @staticmethod
    def defaults():
        return BiiIgnore.loads(default_bii_ignore)

    @staticmethod
    def loads(text, prefix=None):
        result = BiiIgnore()
        for (line_no, line) in enumerate(text.splitlines()):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                accept = False
                if line[0] == '!':
                    accept = True
                    line = line[1:]
                if prefix:
                    line = prefix + '/' + line
                result.append((line, accept))
            except Exception:
                raise BiiException('Wrong bii_ignore format in line %d: %s' (line_no, line))
        return result

    def ignored(self, name):
        '''@return: True if it should be ignored'''
        ignored = False
        max_cache = fnmatch._MAXCACHE
        num_elements = len(self)
        fnmatch._MAXCACHE = num_elements if num_elements > max_cache else max_cache
        for pattern, accept in self:
            if (ignored and accept) or (not ignored and not accept):
                if fnmatch.fnmatch(name, pattern):
                    ignored = not ignored
        fnmatch._MAXCACHE = max_cache  # Restoring original cache value
        return ignored
