"""MySQL connections with explicit transactions and deterministic cleanup."""
import pymysql
from pymysql.constants import CLIENT
from . import config

IntegrityError = pymysql.IntegrityError


class Row(dict):
    """Named fields, with positional access for aggregate queries."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class Cursor(pymysql.cursors.DictCursor):
    def fetchone(self):
        row = super().fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return tuple(Row(row) for row in super().fetchall())

    def fetchmany(self, size=None):
        return tuple(Row(row) for row in super().fetchmany(size))


class ManagedConnection(pymysql.connections.Connection):
    def execute(self, sql, parameters=None):
        cursor = self.cursor()
        cursor.execute(sql, parameters)
        return cursor

    def executemany(self, sql, parameters):
        cursor = self.cursor()
        cursor.executemany(sql, parameters)
        return cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()


def get_connection():
    options = dict(
        host=config.MYSQL_HOST, port=config.MYSQL_PORT,
        user=config.MYSQL_USER, password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE, charset='utf8mb4',
        cursorclass=Cursor, autocommit=False, client_flag=CLIENT.FOUND_ROWS,
        connect_timeout=config.MYSQL_CONNECT_TIMEOUT, read_timeout=30, write_timeout=30,
    )
    if config.MYSQL_SSL_CA:
        options.update(ssl_ca=config.MYSQL_SSL_CA,
                       ssl_verify_cert=True, ssl_verify_identity=True)
    return ManagedConnection(**options)


def init_schema():
    from .mysql_schema import initialize_schema
    with get_connection() as conn:
        initialize_schema(conn)
