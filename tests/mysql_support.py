"""Disposable schemas; never use the application schema or production account."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import uuid

from dotenv import dotenv_values
import pymysql
from backend import config


@contextmanager
def temporary_database():
    settings = {**dotenv_values(Path(__file__).resolve().parents[1] / '.env.test'), **os.environ}
    prefix = 'TOEFL_TEST_MYSQL_'
    if not settings.get(prefix + 'USER'):
        raise RuntimeError('Siapkan .env.test dengan akun khusus database linguapulse_test_*.')
    options = dict(host=settings.get(prefix + 'HOST', '127.0.0.1'),
                   port=int(settings.get(prefix + 'PORT', '3306')),
                   user=settings[prefix + 'USER'], password=settings.get(prefix + 'PASSWORD', ''),
                   charset='utf8mb4', autocommit=True)
    name = 'linguapulse_test_' + uuid.uuid4().hex
    saved = {key: getattr(config, key) for key in
             ('MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE', 'MYSQL_SSL_CA')}
    admin = pymysql.connect(**options)
    try:
        with admin.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
        config.MYSQL_HOST, config.MYSQL_PORT = options['host'], options['port']
        config.MYSQL_USER, config.MYSQL_PASSWORD = options['user'], options['password']
        config.MYSQL_DATABASE = name
        config.MYSQL_SSL_CA = ''
        yield name
    finally:
        for key, value in saved.items():
            setattr(config, key, value)
        try:
            if not re.fullmatch(r'linguapulse_test_[a-f0-9]{32}', name):
                raise RuntimeError('Refusing to drop an unexpected database name')
            with admin.cursor() as cursor:
                cursor.execute(f'DROP DATABASE IF EXISTS `{name}`')
        finally:
            admin.close()
