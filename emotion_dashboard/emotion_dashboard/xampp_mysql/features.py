from django.db.backends.mysql.features import DatabaseFeatures as MySQLFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(MySQLFeatures):
    """Retain Django 5.2 behavior while allowing XAMPP's MariaDB 10.4."""

    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return super().minimum_database_version

    @cached_property
    def can_return_columns_from_insert(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 5)
        return False
