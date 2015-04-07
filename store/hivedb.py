from biicode.common.model.brl.block_cell_name import BlockCellName
import os
from biicode.client.exception import ClientException
from biicode.common.model.content import ContentDeserializer
from biicode.common.api.edition_api import EditionAPI
from biicode.common.edition.hive import Hive
from biicode.client.store.sqlite import SQLiteDB
from biicode.client.migrations.migrations import get_client_migrations
from biicode.common.migrations.migration import Migration
from biicode.common.utils.bii_logging import logger
from biicode.client.store.blob_sqlite import BlobSQLite


def factory(dbpath):
    try:
        if not os.path.exists(dbpath):
            folder = os.path.dirname(dbpath)
            if not os.path.exists(folder):
                os.makedirs(folder)
            db = HiveDB(dbpath)
            db.connect()
            # Init database with last migration, we are creating it with last version
            db.init(get_client_migrations().pop())
        else:
            db = HiveDB(dbpath)
            db.connect()
        return db
    except Exception as e:
        logger.error(e)
        raise ClientException("Could not initialize local cache", e)

CELLS = "cells"
CONTENTS = "contents"
HIVES = "hives"
VERSION = "client_version"


class HiveDB(BlobSQLite, EditionAPI):

    def __init__(self, dbfile):
        super(HiveDB, self).__init__(dbfile)

    def init(self, last_client_migration):
        try:
            SQLiteDB.init(self)
            statement = self.connection.cursor()
            self.create_table(statement, HIVES)
            self.create_table(statement, CELLS)
            self.create_table(statement, CONTENTS)
            self.create_table(statement, VERSION)
            # Last migrated version is last migration available
            self.upsert_last_migrated(last_client_migration)

        except Exception as e:
            raise ClientException("Could not initalize local cache", e)

    def read_hive(self):
        return self.read('hive_id', HIVES, Hive)

    def read_edition_contents(self, block_cell_names):
        return self.read_multi(block_cell_names, CONTENTS, ContentDeserializer(BlockCellName))

    def upsert_hive(self, hive):
        return self.upsert('hive_id', hive, HIVES)

    def upsert_edition_contents(self, contents):
        rows = [(c.ID, c) for c in contents]
        return self.upsert_multi(rows, CONTENTS)

    def delete_edition_contents(self, block_cell_names):
        result = self.delete_multi(block_cell_names, CONTENTS)
        return result

    def upsert_last_migrated(self, migration):
        self.upsert('last_migrated', migration, VERSION)

    def read_last_migrated(self):
        """Last migrated version"""
        return self.read('last_migrated', VERSION, Migration)

    def clean(self):
        self.delete_all(CELLS)
        self.delete_all(CONTENTS)
        self.upsert_hive(Hive())
        self.vacuum()
