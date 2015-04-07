'''
Class for manage SQLite databases with tables with fields id and blob (BLOB)
for table content
'''
from biicode.common.exception import NotInStoreException
from biicode.client.store.sqlite import SQLiteDB, encode_serialized_value,\
    decode_serialized_value
from biicode.common.utils.serializer import serialize


class BlobSQLite(SQLiteDB):

    def create_table(self, cursor, table):
        cursor.execute("create table if not exists %s (id TEXT UNIQUE, blob BLOB)" % table)

    def read(self, ID, table, deserializer):
        query = "SELECT blob FROM %s WHERE id=\"%s\"" % (table, ID)
        c = self.connection.cursor()
        c.execute(query)
        rs = c.fetchone()
        if not rs:
            raise NotInStoreException('Not found %s in %s' % (ID, table))
        data = decode_serialized_value(rs[0])
        item = None
        if deserializer is not None:
            if hasattr(deserializer, 'deserialize'):
                item = deserializer.deserialize(data)
            else:
                item = deserializer(data)
        else:  # Don't want deserialization
            return data

        if item is None:
            raise NotInStoreException('Not found %s in %s' % (ID, table))
        return item

    def read_multi(self, ids, table, deserializer):
        result = {}
        for chunked_ids in self._chunks(ids):
            query = "SELECT blob FROM %s WHERE id in (%s)" % (table,
                                        ', '.join(['?'] * len(chunked_ids)))
            c = self.connection.cursor()
            c.execute(query, list(chunked_ids))
            rss = c.fetchall()
            for rs in rss:
                data = decode_serialized_value(rs[0])  # dict repr() to dict
                item = deserializer.deserialize(data)
                if item:
                    result[item.ID] = item
        return result

    def create(self, ID, value, table):
        self._generic_write(table, ID, encode_serialized_value(serialize(value)),
                            'id', 'blob', 'INSERT')

    def update(self, ID, value, table):
        self._generic_write(table, ID, encode_serialized_value(serialize(value)),
                            'id', 'blob', 'REPLACE')

    def upsert(self, ID, value, table):
        serial_value = serialize(value)
        self._generic_write(table, ID, encode_serialized_value(serial_value),
                            'id', 'blob', 'INSERT OR REPLACE')

    def create_multi(self, id_value_list, table):
        self._generic_write_multi(table, id_value_list, 'id', 'blob', 'INSERT')

    def update_multi(self, id_value_list, table):
        self._generic_write_multi(table, id_value_list, 'id', 'blob', 'REPLACE')

    def upsert_multi(self, id_value_list, table):
        self._generic_write_multi(table, id_value_list, 'id', 'blob', 'INSERT OR REPLACE')
