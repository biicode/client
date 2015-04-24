import sqlite3
from biicode.client.exception import ClientException
import os


class SQLiteDB(object):
    def __init__(self, dbfile_path):
        if not os.path.exists(dbfile_path):
            par = os.path.dirname(dbfile_path)
            if not os.path.exists(par):
                os.makedirs(par)
            dbfile = open(dbfile_path, 'w+')
            dbfile.close()
        self.dbfile = dbfile_path

    def init(self):
        """Called when database doesn't exist"""
        try:
            statement = self.connection.cursor()
            statement.execute("PRAGMA auto_vacuum = INCREMENTAL;")
        except Exception as e:
            raise ClientException("Could not initialize local cache", e)

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.dbfile,
                                              detect_types=sqlite3.PARSE_DECLTYPES)
            self.connection.text_factory = str
        except Exception as e:
            raise ClientException('Could not connect to local cache', e)

    def disconnect(self):
        self.connection.close()

    def _generic_write(self, table, key, value, key_field, value_field,
                       write='INSERT OR REPLACE'):
        statement = self.connection.cursor()
        query = "%s INTO %s (%s, %s) VALUES (?, ?)" % (write, table,
                                                       key_field,
                                                       value_field)
        statement.execute(query, (key, value))
        self.connection.commit()

    def _generic_write_multi(self, table, id_value_list, key_field,
                             value_field, write='INSERT OR REPLACE'):
        '''
        Params: id_value_list: [(k1, v2), (k2, v2), ..., (kn, vn)]
        '''
        serial_rows = [(str(ID), encode_serialized_value(obj.serialize()))
                       for ID, obj in id_value_list]
        c = self.connection.cursor()
        query = "%s INTO %s (%s, %s) VALUES (?, ?)" % (write, table,
                                                       key_field, value_field)
        c.executemany(query, serial_rows)
        self.connection.commit()

    def delete(self, ID, table):
        statement = self.connection.cursor()
        command = 'DELETE from %s where id=(?)' % table
        statement.execute(command, (ID,))
        self.connection.commit()

    def delete_multi(self, IDs, table):
        c = self.connection.cursor()
        command = "DELETE from %s where id=(?)" % (table)
        c.executemany(command, [[ID] for ID in IDs])

    def delete_all(self, table):
        statement = self.connection.cursor()
        command = "DELETE FROM %s;" % (table)
        statement.execute(command)
        self.connection.commit()

    def vacuum(self):
        '''
        The VACUUM command cleans the main database by copying its contents to a temporary database
        file and reloading the original database file from the copy. This eliminates free pages,
        aligns table data to be contiguous, and otherwise cleans up the database file structure.

        The VACUUM command may change the ROWID of entries in tables that do not have an explicit
        INTEGER PRIMARY KEY. The VACUUM command only works on the main database.
        It is not possible to VACUUM an attached database file.

        The VACUUM command will fail if there is an active transaction.
        The VACUUM command is a no-op for in-memory databases.
        As the VACUUM command rebuilds the database file from scratch, VACUUM can also be used to
        modify many database-specific configuration parameters.
        '''
        c = self.connection.cursor()
        c.execute('VACUUM;')


def encode_serialized_value(value):
    '''json is other way to do it if value was a dict
       can even be replaced here with pickle but is less legible'''
    return value.__repr__()


def decode_serialized_value(value):
    '''json is other way to do it if value was a dict
   can even be replaced here with pickle but is less legible'''
    from bson.binary import Binary  # DO NOT REMOVE! Necessary for eval
    return eval(value)
