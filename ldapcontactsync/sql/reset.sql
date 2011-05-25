-- SugarCRM-LDAP Sync modifications - reset all syn cstatus (when for example you'have deleted the whole LDAP branch
-- SQL COMMANDS
-- If your base is not 'sugarcrm' then adjust it here.
USE sugarcrm ;
UPDATE contacts SET ldap_sync=0 ;
UPDATE accounts_contacts SET ldap_sync=0 ;
UPDATE accounts SET ldap_sync=0 ;
UPDATE email_addresses SET ldap_sync=0 ;
UPDATE email_addr_bean_rel SET ldap_sync=0 ;
UPDATE contacts_cstm SET ldap_sync=0 ;
UPDATE accounts_cstm SET ldap_sync=0 ;
UPDATE users SET ldap_sync=0;
-- END SQL COMMANDS

