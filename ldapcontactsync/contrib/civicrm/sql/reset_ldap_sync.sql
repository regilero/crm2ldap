-- CiviCRM-LDAP Sync modifications - reset all sync status (when for example you'have deleted the whole LDAP branch
-- SQL COMMANDS
-- If your base is not 'civicrmdb' then adjust it here.
USE civicrmdb ;
BEGIN; 
SET @DISABLE_TRIGGERS=1; 
UPDATE civicrm_contact set ldap_sync=0; 
SET @DISABLE_TRIGGERS=NULL; COMMIT;
-- END SQL COMMANDS

USE drupaldb;
BEGIN;
SET @DISABLE_TRIGGERS=1;
UPDATE users set ldap_sync=0;
SET @DISABLE_TRIGGERS=NULL; COMMIT;
-- END SQL COMMANDS
