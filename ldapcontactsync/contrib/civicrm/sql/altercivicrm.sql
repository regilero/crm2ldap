-- CiviCRM-LDAP Sync modifications
-- adding some triggers to detect changes from CiviCRM
-- SQL COMMANDS
-- If your base is not 'civicrmdb' then adjust it here.
-- ldap_sync status is:
--	0: not initialized : this field was reset via reset.sql or as yet never been recorded in LDAP
--	1: sync : OK, this field is normally in the same state in LDAP (if he should be there)
--	2: sync started : sync is actually running on this field, or as stopped before the end, the --force option of sync script can recheck that row
--	3: not sync anymore : field has been updated in MySQL and not yet in LDAP, it will comme soon

USE civicrmdb ;
ALTER TABLE civicrm_contact ADD COLUMN ldap_sync TINYINT DEFAULT 0;
-- ldap_sync_tag_as_drupal_user is a marker set on the contact to retain this contact was related to a drupal user
-- it will be activted during ldap synchronisation
-- the main goal of this marker is to detect this record is not anymore associated to a drupal user, which means
-- this Drupal user was deleted. So it will be used by the Drupal user synchronisation process
-- to detect drupal user deletion, irt ha no impact on caontact synchronisation
-- value: 0 : not related or unknown 1: known to be related to a drupal user
-- ALTER TABLE civicrm_contact ADD COLUMN ldap_sync_tag_as_drupal_user TINYINT DEFAULT 0;
-- ALTER TABLE civicrm_contact ADD COLUMN ldap_sync_related_drupal_user int(10) unsigned NOT NULL DEFAULT 0;
-- add some index
CREATE INDEX civicrm_contact_idx_ldap_sync ON civicrm_contact (ldap_sync) ;
-- CREATE INDEX civicrm_contact_idx_ldap_sync_tag ON civicrm_contact (ldap_sync_tag_as_drupal_user) ;

-- Triggers
DROP TRIGGER IF EXISTS syncldap_contacts_beforeupdate ;

delimiter //
CREATE trigger syncldap_contacts_beforeupdate BEFORE UPDATE ON civicrm_contact FOR EACH ROW BEGIN
   IF (@DISABLE_TRIGGERS IS NULL) THEN
     SET NEW.ldap_sync=3;
   END IF;
END;//

delimiter ;

-- TODO: cron cleanup deleted: we should make sure the cleanup cron checks for ldap_sync = 1 (OK) before really deleting a contact

-- For users sync if Drupal name or password are modified
USE drupaldb ;
ALTER TABLE users ADD COLUMN ldap_sync TINYINT DEFAULT 0;
CREATE TABLE `ldap_sync_deleted_users` (
  `uid` int(10) unsigned NOT NULL DEFAULT 0, 
  `name` varchar(60) NOT NULL DEFAULT '',
  `login` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`uid`)
) ENGINE=MyISAM CHARSET=utf8;

-- add some index
CREATE INDEX users_idx_ldap_sync ON users (ldap_sync) ;

DROP TRIGGER IF EXISTS syncldap_users_beforeupdate ;
DROP TRIGGER IF EXISTS syncldap_users_deleted ;

delimiter //
-- for users sync
CREATE TRIGGER syncldap_users_beforeupdate BEFORE UPDATE ON users FOR EACH ROW BEGIN
   IF (@DISABLE_TRIGGERS IS NULL) THEN
        IF ((NEW.name <> OLD.name) OR (NEW.pass <> OLD.pass) OR (NEW.mail <> OLD.mail))THEN 
           SET NEW.ldap_sync=3; 
        END IF; 
   END IF;
END;//
-- for deleted users sync, i.e. user removal in LDAP
CREATE TRIGGER syncldap_users_deleted AFTER DELETE ON users FOR EACH ROW BEGIN
    INSERT INTO `ldap_sync_deleted_users` (`uid`,`name`,`login`) VALUES (OLD.uid,OLD.name,OLD.login);
END;//
delimiter ;
-- END SQL COMMANDS
