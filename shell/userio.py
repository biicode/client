from biicode.client.shell.biistream import BiiOutputStream
from biicode.common.exception import InvalidNameException
import getpass
from StringIO import StringIO
from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.utils.bii_logging import logger
from biicode.common.utils.validators import valid_ip
from biicode.common.exception import BiiException
from biicode.common.output_stream import OutputStream
import sys


class UserIO(object):
    """Class to interact with the user, used to show messages and ask for information"""
    def __init__(self, ins=sys.stdin, out=None):
        '''
        Params:
            ins: input stream
            out: output stream, should have write method
        '''
        self._ins = ins
        if not out:
            out = OutputStream(sys.stdout)
        self._out = out

    @property
    def out(self):
        """Get output stream"""
        return self._out

    @property
    def ins(self):
        """Get input stream"""
        return self._ins

    def request_option(self, option_name, args=None, options=None, kls=None,
                       default_option=None, one_line_options=False):
        """
        Asks the user to decide among a list
        Parameters:
            param option_name : Name of option inside args
            param args: List of arguments where to search for the option,
                        if it's not present there, it will prompt the user for it
            param options: option list
            param kls: Returned class (eg: BlockName)
            param default: If user press 'enter', return default option
            param one_line_options: Shows available options in one line
        """
        options = options or []
        if args is None:
            args = []
        value = getattr(args, option_name, None)
        # If an integer parameter is 0, we cant check if getattr(args, option_name)
        if value is None or value == "":
            logger.debug("Not parameter %s in args %s" % (option_name, args))
            if len(options) == 1:
                ret = options.pop()
                self.out.input_text("%s: " % option_name)
                self.out.listitem("%s" % ret, 1)
            else:
                ret = self._request_while(option_name, options, kls, default_option,
                                          one_line_options)
        else:
            ret = self._get_option_from_args(option_name, args, options, kls, default_option)
        return ret

    def print_options(self, options, one_line_options=False):
        """Print options to the user
        :param options Collection of option name to print"""
        if options and len(options) > 0:
            self.out.header("Available options:")
            self.out.header("--------------------------")
            if one_line_options:
                self.out.write(", ".join(options))
                self.out.writeln("")
            else:
                for option in options:
                    self.out.listitem("%s" % option, 1)
            self.out.header("--------------------------")

    def request_login(self, username=None):
        """Request user to input their name and password
        :param username If username is specified it only request password"""
        user_input = ''
        while not username:
            try:
                self.out.input_text('Username: ')
                user_input = raw_input()
                username = BRLUser(user_input)
            except InvalidNameException:
                self.out.error('%s is not a valid username' % user_input)

        self._out.input_text('Please enter a password for "%s" account: ' % username)
        try:
            pwd = getpass.getpass("")
        except Exception as e:
            raise BiiException('Cancelled pass %s' % e)
        return username, pwd

    def request_string(self, msg, default_value=None):
        """Request user to input a msg
        :param msg Name of the msg
        """
        if default_value:
            self._out.input_text('%s (%s): ' % (msg, default_value))
        else:
            self._out.input_text('%s: ' % msg)
        s = self._ins.readline().replace("\n", "")
        if default_value is not None and s == '':
            return default_value
        return s

    def request_ip(self, msg, default_value):
        """Request user to input a ip
        """
        while True:
            try:
                s = self.request_string(msg, default_value)
                valid_ip(s)
                return s
            except Exception:
                self.out.error("Not a valid IP \n")

    def request_boolean(self, msg, default_option=None):
        """Request user to input a boolean"""
        ret = None
        while ret is None:
            if default_option is True:
                s = self.request_string("%s (YES/no)" % msg)
            elif default_option is False:
                s = self.request_string("%s (NO/yes)" % msg)
            else:
                s = self.request_string("%s (yes/no)" % msg)
            if default_option is not None and s == '':
                return default_option
            if s.lower() in ['yes', 'y']:
                ret = True
            elif s.lower() in ['no', 'n']:
                ret = False
            else:
                self.out.error("%s is not a valid answer" % s)
        return ret

    def __repr__(self):
        if isinstance(self.out, StringIO):
            return str(self.out.getvalue())
        if isinstance(self.out, BiiOutputStream):
            return repr(self.out)
        return repr(self.out)

    def _request_while(self, option_name, options, kls, default_option, one_line_options=False):
        str_list_options = ""
        if options:
            str_list_options = "(/o list options)"

        while True:
            #logger.debug("Request to user...")
            str_ = ''
            if not default_option:
                str_ = self.request_string("Enter %s %s" % (option_name, str_list_options))
            else:
                str_ = self.request_string("Enter %s (default:%s) %s"
                                           % (option_name, default_option, str_list_options))
            if str_ == '/o':
                self.print_options(options, one_line_options)
            else:
                if str_ == '' and default_option:
                    return default_option
                if str_.lower() == 'none' and ('none' in options or 'None' in options):
                    return None
                ret = None
                try:
                    ret = kls(str_) if kls is not None else str_
                    if len(options) == 0 or ret in options:
                        return ret
                except (BiiException, AttributeError):
                    pass
                self.out.error("%s is not a valid %s \n" % (str_, option_name))
                self.print_options(options, one_line_options)

    def _get_option_from_args(self, option_name, args, options, kls, default_option,
                              one_line_options=False):
        str_ = getattr(args, option_name)
        if isinstance(str_, list):
            str_ = str_[0]
        try:
            ret = kls(str_) if kls is not None else str_
        except Exception:
            ret = None
        if ret is not None and len(options) == 0 or ret in options:
            return ret
        else:
            self.out.error("%s is not valid %s! \n" % (str_, option_name))
            if options:
                self.print_options(options)
            ret = self._request_while(option_name, options, kls, default_option,
                                      one_line_options=one_line_options)
            return ret
