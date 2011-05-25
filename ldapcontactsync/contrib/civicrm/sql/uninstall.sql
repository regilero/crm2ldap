-- CiviCRM-LDAP Sync modifications removal
-- removing some triggers to detect changes from CiviCRM & Drupal
-- SQL COMMANDS
-- If your base is not 'civicrmdb' then adjust it here.
USE civicrmdb ;
DROP TRIGGER IF EXISTS syncldap_contacts_beforeupdate ;
ALTER TABLE civicrm_contact DROP COLUMN ldap_sync;

USE drupaldb ;
DROP TRIGGER IF EXISTS syncldap_users_beforeupdate ;
DROP TRIGGER IF EXISTS syncldap_users_delete ;
ALTER TABLE users DROP COLUMN ldap_sync ;
DROP TABLE IF EXISTS ldap_sync_deleted_users ;
-- END SQL COMMANDS
