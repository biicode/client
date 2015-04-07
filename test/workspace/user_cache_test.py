
from unittest import TestCase
import tempfile
import os
from biicode.common.test.conf import BII_TEST_FOLDER
from biicode.common.utils.file_utils import load
from biicode.client.workspace.user_cache import UserCache


class UserCacheTest(TestCase):

    def setUp(self):
        # create a workspace temp dir
        self.user_folder = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.biicode_folder = os.path.join(self.user_folder, '.biicode')
        self.user_cache = UserCache(self.biicode_folder)

    def test_initialize(self):
        """ Presence of WS configuration files
        """
        self.user_cache.bii_ignore
        # default_bii_ignore.bii
        path = os.path.join(self.biicode_folder, 'ignore.bii')
        c = load(path)
        self.assertIn('# Format is as follows:', c)
        self.assertIn('# Hidden files', c)

        self.user_cache.default_policies
        path = os.path.join(self.biicode_folder, 'default_policies.bii')
        c = load(path)
        self.assertIn('# This file configures', c)

        self.user_cache.localdb
        path = os.path.join(self.biicode_folder, 'bii.db')
        self.assertTrue(os.path.exists(path), path + ' does not exist.')
