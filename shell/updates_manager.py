'''
Get ServerInfo from BiicodeRestApi. Alert user for downloading new version
and check for deprecated client installed.
'''
import datetime
from biicode.common.model.server_info import ClientVersion, ServerInfo
from biicode.client.exception import ObsoleteClient
from biicode.common.utils.file_utils import save, load
import cPickle as pickle
from biicode.common.utils.bii_logging import logger


class UpdateInfo(object):
    """Model for info to write on disk.
    ServerInfo + datetime"""
    DATE_PATTERN = '%Y-%m-%d %H:%M'

    def __init__(self, server_info=None, time=None):
        self.server_info = server_info
        self.time = time
        if time:
            self.time = UpdateInfo._round_datetime(time)

    @staticmethod
    def deserialize(data):
        """Loads date and server info"""
        server_info = ServerInfo.deserialize(data[0])
        time = datetime.datetime.strptime(data[1], UpdateInfo.DATE_PATTERN)
        return UpdateInfo(server_info, time)

    def serialize(self):
        """Pickelize a tuple with server_info and time"""
        ser_date = self.time.strftime(UpdateInfo.DATE_PATTERN)
        ser_info = self.server_info.serialize()
        return (ser_info, ser_date)

    def __eq__(self, other):
        if self is other:
            return True
        if isinstance(other, self.__class__):
            return self.server_info == other.server_info and \
                   self.time == other.time
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def _round_datetime(thedatetime):
        tmp = thedatetime.strftime(UpdateInfo.DATE_PATTERN)
        return datetime.datetime.strptime(tmp, UpdateInfo.DATE_PATTERN)


class PickleFileStore(object):
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

    def save(self, model):
        """Saves to file"""
        data = model.serialize()
        data = pickle.dumps(data)
        save(self.config_file_path, data)

    def load(self, deserializer):
        data = load(self.config_file_path)
        info = pickle.loads(data)
        return deserializer().deserialize(info)


class UpdatesStore(PickleFileStore):
    """Saves and loads updates information (ServerInfo + Datetime of the check)"""

    def load(self):
        try:
            return super(UpdatesStore, self).load(UpdateInfo)
        except Exception:
            return UpdateInfo(None, None)


class UpdatesManager(object):
    """Check for updates in server each TIME_BETWEEN_CHECKS"""
    TIME_BETWEEN_CHECKS = datetime.timedelta(hours=6)
    FILE_LAST_CHECK = ".updates"

    def __init__(self, store, biiapi, client_version, time_between_checks=None):
        assert(isinstance(client_version, ClientVersion))
        self.client_version = client_version
        self.biiapi = biiapi
        self.store = store
        self.time_between_checks = time_between_checks or self.TIME_BETWEEN_CHECKS

    def check_for_updates(self, biiout):
        """Calls get_server_info in remote api if TIME_BETWEEN_CHECKS have passed"""
        update_info = self.store.load()
        server_info = update_info.server_info
        last_check = update_info.time
        now = datetime.datetime.utcnow()
        # If we don't have information yet or its old information
        if last_check is None or (last_check + self.time_between_checks) <= now:
            try:
                server_info = self.biiapi.get_server_info()
            except Exception as e:  # Don't care if we can't call. continue working
                logger.debug(e)
                server_info = ServerInfo()
            self.store.save(UpdateInfo(server_info, now))
        # If have not passed TIME_BETWEEN_CHECKS, process old server_info
        return self._process_server_info(server_info, biiout)

    def _process_server_info(self, server_info, biiout):
        if not server_info:
            return

        if server_info.version > self.client_version:
            biiout.info("There is a new version of biicode. Download it at %s"
                          % server_info.download_url)
        if not self.client_version == 'develop' and \
           server_info.last_compatible > self.client_version:
            raise ObsoleteClient("Your current version is deprecated and won't work any longer")
        if server_info.messages:
            biiout.info(server_info.messages)
