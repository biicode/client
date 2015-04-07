from biicode.common.exception import BiiException


class ClientException(BiiException):
    '''Generic client exception, raised in controlled scenarios'''
    pass


class ConnectionErrorException(ClientException):
    pass


class ObsoleteClient(ClientException):
    pass


class NotInAHiveException(ClientException):
    '''Raised when we cwd it's not inside a hive but it's expected so'''
    def __init__(self, *args, **kwargs):
        ClientException.__init__(self, "You're not in a valid project folder", *args, **kwargs)
