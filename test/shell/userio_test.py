from unittest import TestCase
from biicode.client.shell.userio import UserIO
from biicode.client.shell.biistream import BiiOutputStream
from StringIO import StringIO
from collections import namedtuple
from mock import Mock


class TestUserIO(TestCase):
    def setUp(self):
        out = BiiOutputStream()
        ins = StringIO()
        self.paths = UserIO(ins, out)
        self.paths._request_while = Mock(side_effect=Exception('Boom!'))

    def test_request_boolean(self):
        self.paths.ins.write('yes')
        self.paths.ins.seek(0)
        self.assertTrue(self.paths.request_boolean('msg'))

        self.paths.ins.truncate(0)
        self.paths.ins.write('no')
        self.paths.ins.seek(0)
        self.assertFalse(self.paths.request_boolean('msg'))

        self.paths.ins.truncate(0)
        self.paths.ins.write('yds\nyes\n')
        self.paths.ins.seek(0)
        self.assertTrue(self.paths.request_boolean('msg'))

    def test_request_option(self):
        Namespace = namedtuple('Namespace', ['block', 'description', 'name', 'version'])
        args = Namespace(block='dummy/dummy/geom/master', description='description example',
                         name='geom2', version='0')
        version = self.paths._get_option_from_args('version', args, [], type(0), None)
        self.assertEquals(version, 0)
