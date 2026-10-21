import os

_DB = os.environ['DATABASE_URL']


class Config:
    SECRET_KEY = os.urandom(16)
    SQLALCHEMY_DATABASE_URI = _DB
    SQLALCHEMY_BINDS = {
        'whitelist_db': os.environ.get('WHITELIST_DATABASE_URL', _DB)
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 'users' is a key that we need to write into the class


class ProdConfig(Config):
    DEBUG = False


class DevConfig(Config):
    DEBUG = True