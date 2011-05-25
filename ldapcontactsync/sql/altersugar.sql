-- SugarCRM-LDAP Sync modifications
-- adding some triggers to detect changes from SugarCRM
-- SQL COMMANDS
-- If your base is not 'sugarcrm' then adjust it here.
USE sugarcrm ;
ALTER TABLE contacts DROP COLUMN ldap_uid ;
ALTER TABLE contacts ADD COLUMN ldap_uid INTEGER UNIQUE NOT NULL AUTO_INCREMENT;
ALTER TABLE contacts ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE accounts_contacts ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE accounts ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE email_addresses ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE email_addr_bean_rel ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE contacts_cstm ADD COLUMN ldap_sync TINYINT DEFAULT 0;
ALTER TABLE accounts_cstm ADD COLUMN ldap_sync TINYINT DEFAULT 0;
-- for users sync
ALTER TABLE users ADD COLUMN ldap_uid INTEGER UNIQUE NOT NULL AUTO_INCREMENT;
ALTER TABLE users ADD COLUMN ldap_sync TINYINT DEFAULT 0;

DROP TRIGGER IF EXISTS syncldap_contacts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_contacts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_email_addr_bean_rel_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_emailaddresses_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_contacts_cstm_beforeupdate;
DROP TRIGGER IF EXISTS syncldap_accounts_cstm_beforeupdate;
-- for users sync
DROP TRIGGER IF EXISTS syncldap_users_beforeupdate;

delimiter //
CREATE TRIGGER syncldap_contacts_beforeupdate BEFORE UPDATE ON contacts FOR EACH ROW 
        BEGIN IF (NEW.date_modified <> OLD.date_modified) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_accounts_contacts_beforeupdate BEFORE UPDATE ON accounts_contacts FOR EACH ROW 
        BEGIN IF (NEW.date_modified <> OLD.date_modified) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_accounts_beforeupdate BEFORE UPDATE ON accounts FOR EACH ROW 
        BEGIN IF (NEW.date_modified <> OLD.date_modified) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_email_addr_bean_rel_beforeupdate BEFORE UPDATE ON email_addr_bean_rel FOR EACH ROW 
        BEGIN IF (NEW.date_modified <> OLD.date_modified) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_emailaddresses_beforeupdate BEFORE UPDATE ON email_addresses FOR EACH ROW 
        BEGIN IF (NEW.date_modified <> OLD.date_modified) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_contacts_cstm_beforeupdate BEFORE UPDATE ON contacts_cstm FOR EACH ROW
        BEGIN IF(NEW.ldap_sync=old.ldap_sync) THEN SET NEW.ldap_sync=3; END IF; END;//
CREATE TRIGGER syncldap_accounts_cstm_beforeupdate BEFORE UPDATE ON accounts_cstm FOR EACH ROW
        BEGIN IF(NEW.ldap_sync=old.ldap_sync) THEN SET NEW.ldap_sync=3; END IF; END;//
-- for users sync
CREATE TRIGGER syncldap_users_beforeupdate BEFORE UPDATE ON users FOR EACH ROW
        BEGIN IF ((NEW.date_modified <> OLD.date_modified) OR (NEW.user_hash <> OLD.user_hash))THEN SET NEW.ldap_sync=3; END IF; END;//
delimiter ;
-- END SQL COMMANDS

