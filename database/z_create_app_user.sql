

GRANT SELECT, INSERT, UPDATE, DELETE ON resort_db.* TO 'resort_app'@'%';
GRANT EXECUTE ON resort_db.* TO 'resort_app'@'%';

FLUSH PRIVILEGES;

SHOW GRANTS FOR 'resort_app'@'%';