from mock import Mock
import StringIO
from biicode.client.shell.biistream import BiiOutputStream
from biicode.client.shell.userio import UserIO


def mock_user_io(user_io, request_strings=None, login=None):
    """
    :param user_io: UserIO object to mock (from mocked_user_io)
    :param request_strings: dict of strings with label of request and value to respond.
                           ex: {'yes/no': 'no'} or {'ide': 'none'}
    :param login: Response to request_login (user, pass) or a list of (user, pass).
                  If parameter is a list of (user, token) will respond the 'i'
                  element for each call to request_login.
                  ex: mock_user_io(bii.user_io, login=('dummy', 'bii_ping_pong'))
                  ex: mock_user_io(bii.user_io, login=[('dummy', 'bii_ping_pong'),
                                                       ('other','tok')])
    """
    if isinstance(login, tuple):
        user_io.request_login = Mock(return_value=login)
    elif isinstance(login, list):
        class FakeMock(Mock):
            count_request = 0

            def aux_request_login(self, *args):
                self.count_request += 1
                try:
                    return login[self.count_request - 1]
                except IndexError:
                    raise Exception('Unhandled user login request %s' % args[0])
        user_io.request_login = FakeMock().aux_request_login
    else:
        user_io.request_login = Mock(side_effect=Exception('Requested login in UserIO'))
    mock_strings(user_io, request_strings)


def mock_strings(user_io, request_strings):
    if request_strings:
        def aux(*args):
            for request_string, value in request_strings.iteritems():
                if request_string in args[0]:
                    return value
            raise Exception('Unhandled user input request %s' % args[0])
        user_io.request_string = Mock(side_effect=aux)
    else:
        user_io.request_string = Mock(side_effect=Exception('Requested string in UserIO'))


def mocked_user_io(login=None):
    user_io = UserIO(out=BiiOutputStream(StringIO.StringIO()))
    mock_user_io(user_io, login=login)
    return user_io
