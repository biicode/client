'''
Tests for client/shell/updates_manager_test.py
'''
import unittest
from biicode.client.shell.updates_manager import (UpdatesManager, UpdatesStore,
    UpdateInfo)
from biicode.common.test.bii_test_case import BiiTestCase
from mock import Mock
from biicode.common.model.server_info import ServerInfo, ClientVersion
import datetime
import os
from biicode.client.exception import ObsoleteClient
from biicode.client.test.shell.user_io_mock import mocked_user_io
from biicode.common.output_stream import OutputStream


class UpdatesStoreTest(BiiTestCase):

    def setUp(self):
        BiiTestCase.setUp(self)
        self.folder = self.new_tmp_folder()
        self.file_path = os.path.join(self.folder, ".updates.bii")
        self.store = UpdatesStore(self.file_path)

    def model_serialization_test(self):
        server_info = ServerInfo(ClientVersion("0.9"), 'Hey!', "0.9")
        now = datetime.datetime.utcnow()
        info = UpdateInfo(server_info, now)
        seri = info.serialize()
        dese = UpdateInfo.deserialize(seri)
        self.assertEquals(info, dese)

    def test_save_and_load(self):
        server_info = ServerInfo(ClientVersion("0.9"), 'Hey!', "0.9")
        now = datetime.datetime.utcnow()
        info = UpdateInfo(server_info, now)
        self.store.save(info)

        self.assertTrue(os.path.exists(self.file_path))

        update_info = self.store.load()

        self.assertEquals(update_info.server_info, server_info)
        self.assertEquals(update_info.time, info.time)


class MockStore(object):

    update_info = UpdateInfo(None, None)

    def save(self, update_info):
        self.update_info = update_info

    def load(self):
        return self.update_info


class UpdatesManagerTest(BiiTestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.folder = self.new_tmp_folder()
        self.file_path = os.path.join(self.folder, ".updates.bii")
        self.biiapi = Mock()
        self.user_io = mocked_user_io()
        self.store = MockStore()

    def test_not_checked_ever(self):
        """Even out client is obsolete its not time to check yet"""
        server_info = ServerInfo("0.9", 'Hey!', "0.9")
        self.biiapi.get_server_info = Mock(return_value=server_info)

        obsolete_client = ClientVersion("0.8")
        manager = UpdatesManager(self.store, self.biiapi, obsolete_client,
                                 time_between_checks=datetime.timedelta(days=10))
        self.assertRaises(ObsoleteClient, manager.check_for_updates, self.user_io.out)
        self.assertEquals(self.user_io.out.stream.buf, "")
        # Information is saved
        self.assertEquals(self.store.load().server_info, server_info)

        # Now check again (not needed), it must be the same info and get_server_info
        # was not called
        self.biiapi.get_server_info.call_count = 0
        self.assertRaises(ObsoleteClient, manager.check_for_updates, self.user_io.out)
        self.assertEquals(self.biiapi.get_server_info.call_count, 0)
        self.assertEquals(self.store.load().server_info, server_info)

    def test_check_needed(self):

        server_info = ServerInfo(version="0.9",
                                 message='Hey!', last_compatible="0.5")
        self.biiapi.get_server_info = Mock(return_value=server_info)

        manager = UpdatesManager(self.store, self.biiapi, ClientVersion("0.8"))

        last_time = self._save_info(manager, server_info, datetime.timedelta(days=-365))

        biiout = OutputStream()
        manager.check_for_updates(biiout)
        self.assert_in_response(biiout, "There is a new version of biicode")
        update_info = manager.store.load()
        self.assertNotEquals(update_info.time, last_time)

    def test_higher_version_ok(self):

        server_info = ServerInfo(version="0.9",
                                 message='Hey!', last_compatible="0.5")
        self.biiapi.get_server_info = Mock(return_value=server_info)

        manager = UpdatesManager(self.store, self.biiapi, ClientVersion("1.0"))

        last_time = self._save_info(manager, server_info, datetime.timedelta(days=-365))

        biiout = OutputStream()
        manager.check_for_updates(biiout)
        self.assert_not_in_response(biiout, "There is a new version of biicode")

    def _save_info(self, manager, server_info, timedelta):
        now = datetime.datetime.utcnow()
        thetime = now + timedelta
        tmp = thetime.strftime(UpdateInfo.DATE_PATTERN)
        roundthetime = datetime.datetime.strptime(tmp, UpdateInfo.DATE_PATTERN)
        manager.store.save(UpdateInfo(server_info, roundthetime))

        return server_info, roundthetime
