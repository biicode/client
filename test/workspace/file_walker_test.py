from unittest import TestCase
import tempfile
import os
from nose.plugins.attrib import attr
from biicode.common.test.conf import BII_TEST_FOLDER
from biicode.client.workspace.bii_ignore import BiiIgnore
from biicode.client.shell.biistream import BiiOutputStream
from biicode.common.utils.file_utils import save
from biicode.client.workspace.walk_block import walk_bii_folder, walk_anonymous_block
from biicode.client.workspace.bii_paths import BiiPaths
from biicode.client.workspace.bii_paths import (BII_DIR, BII_HIVE_DB)
from biicode.common.model.brl.block_name import BlockName
import platform
import unittest


class BiiPathsMock(BiiPaths):
    def __init__(self, root, layout, user_home):
        BiiPaths.__init__(self, root, user_home)

        os.mkdir(os.path.join(root, BII_DIR))  # bii/ folder
        save(os.path.join(root, BII_DIR, BII_HIVE_DB), '')  # fake database file
        save(os.path.join(root, BII_DIR, 'layout.bii'), layout)  # layout file


@attr('integration')
class FileWalkerTest(TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.user_home = tempfile.mkdtemp(suffix='biicode', dir=BII_TEST_FOLDER)
        self.biiout = BiiOutputStream()

    def _get_files(self):
        for root, _, files in os.walk(self.folder):
            for filename in files:
                yield os.path.relpath(os.path.join(root, filename), self.folder)

    def test_src_default_accepted(self):
        bii_ignore = BiiIgnore.defaults()
        save(os.path.join(self.folder, 'User/Block/myFile.cpp'), '')

        src_files = walk_bii_folder(self.folder, bii_ignore, self.biiout)
        self.assertEqual(['User/Block/myFile.cpp'], src_files.keys())

        # Check disk
        disk_src_files = set([f.replace('\\', '/') for f in self._get_files()])
        self.assertEqual({'User/Block/myFile.cpp'},
                         disk_src_files)

    def test_src_default_ignored(self):
        bii_ignore = BiiIgnore.defaults()

        save(os.path.join(self.folder, 'User/Block/.myFile.cpp'), '')
        save(os.path.join(self.folder, 'User/Block/myFile.cpp~'), '')
        save(os.path.join(self.folder, 'User2/Block2/Path/To/HelloWorld.obj'), '')

        src_files = walk_bii_folder(self.folder, bii_ignore, self.biiout)

        src_files = {name: t for name, (t, _) in src_files.iteritems()}
        self.assertEqual({}, src_files)

        # Check disk
        disk_src_files = set([f.replace('\\', '/') for f in self._get_files()])
        self.assertEqual({'User/Block/.myFile.cpp', 'User2/Block2/Path/To/HelloWorld.obj',
                          'User/Block/myFile.cpp~'},
                          disk_src_files)

    def test_src_custom_ignored(self):
        dest_folder = os.path.join(self.folder, 'User/Block')

        save(os.path.join(dest_folder, 'myFile.cpp'), '')
        save(os.path.join(dest_folder, 'ignore.bii'), '*.kk')
        save(os.path.join(dest_folder, 'subdir1/ignore.bii'), '*.kk1')
        save(os.path.join(dest_folder, 'subdir1/prueba.kk'), '')
        save(os.path.join(dest_folder, 'subdir1/prueba.kk1'), '')
        save(os.path.join(dest_folder, 'subdir1/prueba.kk2'), '')
        save(os.path.join(dest_folder, 'subdir2/ignore.bii'), '*.kk2')
        save(os.path.join(dest_folder, 'subdir2/prueba.kk'), '')
        save(os.path.join(dest_folder, 'subdir2/prueba.kk1'), '')
        save(os.path.join(dest_folder, 'subdir2/prueba.kk2'), '')
        save(os.path.join(dest_folder, 'subdir3/ignore.bii'), 'hello.kk3')
        save(os.path.join(dest_folder, 'subdir3/hello.kk3'), '')
        save(os.path.join(dest_folder, 'subdir4/subdir5/subdir6/ignore.bii'), 'hello.kk5')
        save(os.path.join(dest_folder, 'subdir4/subdir5/subdir6/hello.kk5'), '')

        bii_ignore = BiiIgnore.defaults()
        src_files = walk_bii_folder(self.folder, bii_ignore, self.biiout)

        src_files = src_files.keys()
        self.assertEqual(set(['User/Block/myFile.cpp',
                              'User/Block/ignore.bii',
                              'User/Block/subdir1/ignore.bii',
                              'User/Block/subdir1/prueba.kk2',
                              'User/Block/subdir2/ignore.bii',
                              'User/Block/subdir2/prueba.kk1',
                              'User/Block/subdir3/ignore.bii',
                              'User/Block/subdir4/subdir5/subdir6/ignore.bii']), set(src_files))

        # Check disk
        disk_src_files = set([f.replace('\\', '/') for f in self._get_files()])
        self.assertEqual({'User/Block/myFile.cpp',
                          'User/Block/subdir1/ignore.bii',
                          'User/Block/ignore.bii',
                          'User/Block/subdir2/prueba.kk',
                          'User/Block/subdir2/prueba.kk2',
                          'User/Block/subdir1/prueba.kk2',
                          'User/Block/subdir1/prueba.kk1',
                          'User/Block/subdir2/prueba.kk1',
                          'User/Block/subdir1/prueba.kk',
                          'User/Block/subdir2/ignore.bii',
                          'User/Block/subdir3/ignore.bii',
                          'User/Block/subdir3/hello.kk3',
                          'User/Block/subdir4/subdir5/subdir6/ignore.bii',
                          'User/Block/subdir4/subdir5/subdir6/hello.kk5'},
                          disk_src_files)

    def test_bad_location(self):
        bii_ignore = BiiIgnore.defaults()
        save(os.path.join(self.folder, 'User/mybadFile.cpp'), '')
        _ = walk_bii_folder(self.folder, bii_ignore, self.biiout)
        # Check that the system detected misplaced file
        self.assertIn("WARN: User/mybadFile.cpp is misplaced", str(self.biiout))

    @unittest.skipIf(platform.system() == "Windows", "windows no symlinks")
    def test_symlink_files_simple_block(self):
        '''
        Check if walker follows symlinked files on bii block
        '''
        block_name = 'User/Block'
        block_folder = os.path.join(self.folder, block_name)
        bii_ignore = BiiIgnore.defaults()

        def test_block():
            return walk_bii_folder(self.folder, bii_ignore, self.biiout)

        self._test_symlink_files(block_folder, block_name, test_block)

    @unittest.skipIf(platform.system() == "Windows", "windows no symlinks")
    def test_symlink_files_anonymous_block(self):
        '''
        Check if walker follows symlinked files on anonymous block
        '''
        block_name = 'User/Block'
        bii_ignore = BiiIgnore.defaults()

        def test_anonymous_block():
            bii_paths = BiiPathsMock(self.folder,
                                     'root-block: {}\nauto-root-block: True'.format(block_name),
                                     self.user_home)
            return walk_anonymous_block(bii_paths, bii_ignore, self.biiout, BlockName(block_name))

        self._test_symlink_files(self.folder, block_name, test_anonymous_block)

    def _test_symlink_files(self, block_folder, block_name, process):
        '''
        Check if walker follows symlinked files
        '''

        file_content = 'palmerita'
        foreign_file_content = 'foreign palmerita'

        # Real block files
        files = [
            'file1.file',
            'subdir1/file2.file',
            'subdir1/subdir2/file3.file',
        ]

        # List of file symlinks (source, link name) (Within the block)
        links = [
            (files[0], 'link1.link'),  # Link belongs to the same directory
            (files[1], 'subdir1/subdir2/link2.link'),  # Link goes upwards the directory hierarchy
            (files[2], 'subdir1/link3.link'),  # Link goes downwards the directory hierarchy
        ]

        # List of file symlinks (source, link name) (Link to external file)
        foreign_links = [
            ('ffile1.ffile', 'flink1.flink'),
            ('ffile2.ffile', 'subdir1/flink2.flink'),
            ('ffile3.ffile', 'subdir1/subdir2/flink3.flink')
        ]

        # Create files/links on test folder
        for file_ in [os.path.join(block_folder, x) for x in files]:
            save(file_, file_content)
            assert(os.path.exists(file_))

        for source, dest in [(os.path.join(block_folder, src),
                              os.path.join(block_folder, dest))
                             for src, dest in links]:
            assert(os.path.exists(source))
            os.symlink(source, dest)
            assert(os.path.exists(dest))

        for source, dest in [(os.path.join(block_folder, src),
                              os.path.join(block_folder, dest))
                             for src, dest in foreign_links]:
            save(source, foreign_file_content)
            os.symlink(source, dest)
            assert(os.path.exists(dest))

        # Check results
        collected_files = process()

        def check_file(file_, expected_content):
            key = BlockName(block_name) + file_
            self.assert_(key in collected_files.keys(), '"{}" file not collected'.format(file_))

            content = collected_files[key]
            self.assertEqual(content, expected_content,
                             '"{}" file content does not match:'
                             ' "{}", expected "{}"'.format(file_, content, expected_content))

        for file_ in files:
            check_file(file_, file_content)

        for file_, _ in links:
            check_file(file_, file_content)

        for file_, _ in foreign_links:
            check_file(file_, foreign_file_content)
