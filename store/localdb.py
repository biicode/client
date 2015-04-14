from biicode.client.exception import ClientException
from biicode.client.store.sqlite import SQLiteDB, encode_serialized_value, decode_serialized_value
from biicode.common.model.content import ContentDeserializer
from biicode.common.model.cells import CellDeserializer
from biicode.common.utils.bii_logging import logger
from biicode.common.model.id import ID
from biicode.common.model.symbolic.reference import Reference, ReferencedResources
from biicode.common.model.resource import Resource
from biicode.common.model.symbolic.block_version_table import BlockVersionTable
from biicode.client.store.blob_sqlite import BlobSQLite
from biicode.common.model.brl.cell_name import CellName
from biicode.common.utils.serializer import ListDeserializer
from biicode.common.model.block_delta import BlockDelta
import traceback


PUBLISHED_CELLS = "cells"  # ID => PublishedCell
PUBLISHED_CONTENTS = "contents"  # ID => PublishedContent
SNAPSHOTS = 'snapshots'
# There are more than one reference to same ID, we store ID and the
# cell/content in the previous tables
# (for not repeat contents!)
PUBLISHED_REFERENCES = "refs"  # Reference => Cell ID, Content ID
DEP_TABLES = "dep_tables"
DELTAS = "deltas"


class LocalDB(BlobSQLite):

    def __init__(self, dbfile):
        super(LocalDB, self).__init__(dbfile)
        self.connect()
        self.init()

    def connect(self):
        SQLiteDB.connect(self)
        statement = None
        try:
            statement = self.connection.cursor()
        except Exception as e:
            raise ClientException(e)
        finally:
            if statement:
                statement.close()

    def init(self):
        SQLiteDB.init(self)
        cursor = None
        try:
            cursor = self.connection.cursor()

            self.create_table(cursor, PUBLISHED_CONTENTS)
            self.create_table(cursor, PUBLISHED_CELLS)
            self.create_table(cursor, SNAPSHOTS)
            self.create_table(cursor, DEP_TABLES)
            self.create_table(cursor, DELTAS)

            # To avoid multiple usernames in the login table, use always "login" as id
            cursor.execute("create table if not exists login (id TEXT UNIQUE, "
                           "username TEXT UNIQUE, token TEXT)")
            cursor.execute("create table if not exists %s "
                              "(reference TEXT UNIQUE, cell_id TEXT, content_id TEXT)"
                              % PUBLISHED_REFERENCES)
            cursor.execute("CREATE INDEX if not exists cell_id_index ON %s (cell_id)"
                              % (PUBLISHED_REFERENCES))
            cursor.execute("CREATE INDEX if not exists content_id_index ON %s (content_id)"
                              % (PUBLISHED_REFERENCES))
        except Exception as e:
            message = "Could not initalize local cache"
            raise ClientException(message, e)
        finally:
            if cursor:
                cursor.close()

    def get_login(self):
        '''Returns login credentials.
        This method is also in charge of expiring them.
        '''
        try:
            statement = self.connection.cursor()
            statement.execute('select * from login where id="login"')
            rs = statement.fetchone()
            if not rs:
                return None, None
            name = rs[1]
            token = rs[2]
            return name, token
        except Exception:
            raise ClientException("Could not retrieve login from local cache\n"
                                  "Try removing the .biicode folder in your home folder")

    def get_username(self):
        return self.get_login()[0]

    def set_login(self, login):
        """Login is a tuple of (login, token)"""
        try:
            statement = self.connection.cursor()
            statement.execute("INSERT OR REPLACE INTO login (id, username, token) "
                              "VALUES (?, ?, ?)",
                              ("login", login[0], login[1]))
            self.connection.commit()
        except Exception as e:
            raise ClientException("Could not store credentials in local cache", e)

    def get_dep_table(self, block_version):
        ID = encode_serialized_value(block_version.serialize())
        return self.read(ID, DEP_TABLES, BlockVersionTable)

    def set_dep_table(self, block_version, dep_table):
        assert isinstance(dep_table, BlockVersionTable)
        ID = encode_serialized_value(block_version.serialize())
        self.create(ID, dep_table, DEP_TABLES)

    def get_cells_snapshot(self, block_version):
        ID = encode_serialized_value(block_version.serialize())
        return self.read(ID, SNAPSHOTS, ListDeserializer(CellName))

    def create_cells_snapshot(self, block_version, snapshot):
        """Snapshot is a list with cell names for an specific block version ''' """
        ID = encode_serialized_value(block_version.serialize())
        self.create(ID, snapshot, SNAPSHOTS)

    def get_delta_info(self, block_version):
        ID = encode_serialized_value(block_version.serialize())
        return self.read(ID, DELTAS, BlockDelta)

    def upsert_delta_info(self, block_version, delta_info):
        """Snapshot is a list with cell names for an specific block version ''' """
        # Don't store origin info in localdb (url field crashes because of ://)
        delta_info.origin = None
        ID = encode_serialized_value(block_version.serialize())
        self.upsert(ID, delta_info, DELTAS)

    def remove_dev_references(self, block_version):
        ser_version = encode_serialized_value(block_version.serialize())
        self.delete(ser_version, DEP_TABLES)
        self.delete(ser_version, SNAPSHOTS)
        self.delete(ser_version, DELTAS)

        c = self.connection.cursor()
        command = 'DELETE from {table} where reference LIKE (?);'.format(table=PUBLISHED_REFERENCES)
        c.execute(command, ("%{}%".format(ser_version),))
        self.connection.commit()
        # TODO: What happens to cells & contents? Not deleted?

    def get_published_resources(self, references):
        '''
        Parameters:
            references: a References (biicode.common.model.symbolic.reference.References) object
        '''
        simple_refs = references.explode()  # references object to reference list
        #each reference has to be stored as json string, cause it is a tuple
        ids = ",".join(["\"%s\"" % encode_serialized_value(v.serialize()) for v in simple_refs])
        return self._read_referenced_resources(self.__query_published_references(ids), ID)

    def create_published_resources(self, referenced_resources):
        '''
        Params:
            referenced_resources = ReferencedResources (biicode.common.model.symbolic.reference)
        '''
        statement = self.connection.cursor()
        for reference, resource in referenced_resources.explode().iteritems():
            self._query_create_published_reference(reference, resource, statement)
        self.connection.commit()

    def _read_referenced_resources(self, query, id_type):
        statement = query

        ret = ReferencedResources()
        rs = statement.fetchall()
        cell_des = CellDeserializer(id_type)
        content_des = ContentDeserializer(id_type)
        for r in rs:
            try:
                v = Reference.deserialize(decode_serialized_value(r[0]))
                scontent = decode_serialized_value(r[2]) if r[2] else None
                res = Resource(cell_des.deserialize(decode_serialized_value(r[1])),
                               content_des.deserialize(scontent))
                cell_name = v.ref
                ret[v.block_version][cell_name] = res
                # logger.debug("Local found: %s/%s" % (str(v.block_version), str(cell_name)))
            except Exception as e:
                tb = traceback.format_exc()
                logger.error("Error while reading resources %s" % str(e))
                logger.debug(tb)

        return ret

    def __query_published_references(self, urls):
        q = '''SELECT %(pub_ref)s.reference as reference,
                      %(pub_cells)s.blob as cell,
                      %(pub_contents)s.blob as content
               FROM %(pub_ref)s
               JOIN %(pub_cells)s ON %(pub_ref)s.cell_id=%(pub_cells)s.id
               LEFT JOIN %(pub_contents)s ON %(pub_ref)s.content_id=%(pub_contents)s.id
               WHERE reference IN (%(refs)s)''' % {"pub_ref": PUBLISHED_REFERENCES,
                                                   "pub_cells": PUBLISHED_CELLS,
                                                   "pub_contents": PUBLISHED_CONTENTS,
                                                   "refs": urls}
        statement = self.connection.cursor()
        return statement.execute(q)

    def _query_create_published_reference(self, reference, resource, statement):
        query = ("INSERT OR REPLACE INTO %s (reference, cell_id, content_id) VALUES (?, ?, ?)"
                 % PUBLISHED_REFERENCES)
        content_id = resource.content.ID.__repr__() if resource.content else None
        statement.execute(query, (encode_serialized_value(reference.serialize()),
                                  resource.cell.ID.__repr__(),
                                  content_id))
        query = "REPLACE INTO %s (id, blob) VALUES (?, ?)" % (PUBLISHED_CELLS)
        statement.execute(query, (resource.cell.ID.__repr__(),
                                  encode_serialized_value(resource.cell.serialize())))
        if content_id:
            query = "REPLACE INTO %s (id, blob) VALUES (?, ?)" % (PUBLISHED_CONTENTS)
            statement.execute(query, (resource.content.ID.__repr__(),
                                      encode_serialized_value(resource.content.serialize())))

    def clean(self):
        self.delete_all(PUBLISHED_CELLS)
        self.delete_all(PUBLISHED_CONTENTS)
        self.delete_all(PUBLISHED_REFERENCES)
        self.delete_all(SNAPSHOTS)
        self.delete_all(DEP_TABLES)
        self.delete_all(DELTAS)
        # Never loose who the user is. Only invalidate token
        login, _ = self.get_login()
        self.set_login((login, None))
        self.vacuum()
