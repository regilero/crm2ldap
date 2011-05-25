Introduction
============

GOAL
====
Having a SugarCRM in one side and an OpenLDAP on the other, you'll be able to get all contacts stored by SugarCRM synchronised on the OpenLDAP, somewhere in th etree.
And now you'll have as well users of the SugarCRM stored somewhere in the tree if you want (this is not the same as having an openLDAP authentification based on OpenLDAP).

INSTALL
=======

package debian/ubuntu
---------------------

Requirements:
you'll need python-mysqldb and python-ldap packages
you'll need as well mozilla.schema and extension.schema in /etc/ldap/schemas/ and activate them in your slapd.conf
and you'll need some adjustments on MYSQL's sugarcrm database (triggers essentially, sql files are in the source)
See docs/INSTALL.TXT file given for details

