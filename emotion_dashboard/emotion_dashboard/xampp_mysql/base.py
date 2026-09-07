from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper

from .features import DatabaseFeatures


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures
