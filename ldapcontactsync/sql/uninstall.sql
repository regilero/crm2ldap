-- SugarCRM-LDAP Sync modifications -uninstall
-- SQL COMMANDS
-- If your base is not 'sugarcrm' then adjust it here.
USE sugarcrm ;
ALTER TABLE contacts DROP COLUMN ldap_uid ;
ALTER TABLE contacts DROP COLUMN ldap_sync ;
ALTER TABLE accounts_contacts DROP COLUMN ldap_sync ;
ALTER TABLE accounts DROP COLUMN ldap_sync ;
ALTER TABLE email_addresses DROP COLUMN ldap_sync ;
ALTER TABLE email_addr_bean_rel DROP COLUMN ldap_sync ;
ALTER TABLE contacts_cstm DROP COLUMN ldap_sync ;
ALTER TABLE accounts_cstm DROP COLUMN ldap_sync ;
ALTER TABLE users DROP COLUMN ldap_uid;
ALTER TABLE users DROP COLUMN ldap_sync;
DROP TRIGGER IF EXISTS syncldap_contacts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_contacts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_email_addr_bean_rel_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_emailaddresses_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_contacts_cstm_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_cstm_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_users_beforeupdate;
-- END SQL COMMANDS

