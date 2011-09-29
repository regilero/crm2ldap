Introduction
============

GOAL
====
Having a SugarCRM or CiviCRM in one side and an OpenLDAP on the other, you'll be able to get all contacts stored by SugarCRM synchronised on the OpenLDAP, somewhere in the tree.
And now you'll have as well users of the SugarCRM/CiviCRM stored somewhere in the tree if you want (this is not the same as having an openLDAP authentification based on OpenLDAP).
The Goal is in fact a PUSH process, from my CRM to an LDAP branch, and then from this LDAP branch to a mail client (Outlook/Thunderbird)

INSTALL
=======

package debian/ubuntu
---------------------

Requirements:
you'll need python-mysqldb and python-ldap packages
you'll need as well mozilla.schema and extension.schema in /etc/ldap/schemas/ and activate them in your slapd.conf
and you'll need some adjustments on MYSQL's sugarcrm or civicrm database (triggers essentially, sql files are in the source)
See docs/INSTALL.TXT file given for details


WARNING TRIGGERS
================
Installed triggers can be removed with the uninstall.sql file. Be aware that MySQL triggers can have one side effect on database migration:
* ensure your databases dumps contains triggers (or you'll need to rerun the install script on the new database, without the column creation instructions)
* use root@localhost to create triggers (sql install script) OR ENSURE you USE THE SAME USER/HOST mechanism to access the database on the new DB server: 
  if you did not use root@localhost to create the triggers but foo@localhost, then the triggers are associated with foo@localhost. If on the new server
  foo@localhost is not a known user in MySQL triggers will fail (yes, this is a shame).
