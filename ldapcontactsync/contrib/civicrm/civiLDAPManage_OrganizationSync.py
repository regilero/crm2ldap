#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
civiLDAPManage_OrganizationSync
====================
This script use civiLDAPContact_OrganizationSync script to sync CiviCRM contact base on an OpenLDAP server. This one is the 'main' script.
He detects unsynced contacts and tell the other script to do the job.
By giving him some args you can limit number of contacts treated.
This script includes as well a --report option to get some sync status stats report

see INSTALL.TXT file for long explanations

License: GNU GPL v2
(c) Makina Corpus - 2011
author : Régis Leroy - Guillaume Chéramy
"""
##########
# IMPORTS
import MySQLdb
#import codecs
import sys
from time import strftime
import datetime
import string, os, getopt,subprocess

#########
# DOCS
__version__="0.1"
__author__ = "regis.leroy@makina-corpus.org, guillaume.cheramy@makina-corpus.org"
__usage__ = """
Usage: civiLDAPManage_OrganizationSync.py [-h/-?/--h/--help] [-d] [-s/-v] i[-r/--report] [-f/--force] [-l/--limit LIMIT] PATH
  **-h/-?/--help/--h**
    Show this little help
  **-d**
    Show the whole doc string of this script
  **-s**
    Silent mode
  **-v**
    Verbose mode
  **-r/--report**
    Report mode, retrieve some sync status statistics
  **-f/--force**
    Force ghosts sync records (status ldap_sync=2) to be resync
  **-l/--limit**
    Limit number of handled contacts, running this script every minutes with a limit of 100 records is a good idea
"""

###########
# GLOBALS
###################### BEGIN CUSTOM ZONE ##############################
# Adjust theses settings to your install needs
MYSQL_HOST = 'localhost'
MYSQL_DB_CIVICRM = 'civicrmdb'
# Here we need a user with read access on the MySQL civicrm database
MYSQL_USER = 'mysqluser'
MYSQL_PASS = 'mysqlpassword'
MYSQL_CIVICRM_PREFIX = 'civicrm_' # something like like 'civicrm_' or ''

###################### END CUSTOM ZONE ################################

# Do not touch theses ones, please
VERBOSITY = 1 #values are 0 (silent),1 (normal), 2(debug)
LIMIT = 0
FORCE_COLLECT_MODE = 0
REPORT_MODE = 0
CHILD_PATH="/usr/bin"
ACCOUNT_CUSTOM = False
CONTACT_CUSTOM = False
db = None
###########
# FUNCTIONS
def printer(thestring,log_level,input_encoding='latin1'):
    """handle the console encoding for printing to console and the verbosity

    log_level is 1 or 2, level 2 are displayed only if VERBOSITY is 2 (debug)
    """
    global VERBOSITY
    if (log_level <= VERBOSITY):
        try: 
            uni_string = thestring.decode(input_encoding)
        except UnicodeEncodeError,e:
            uni_string = thestring
        console_encoding = sys.stdout.encoding
        if (console_encoding==None):
            console_encoding='ascii'
        print '+ ' + uni_string.encode(console_encoding,'replace')

def main_parseopts():
    """ Handle args given in the command line.

    Return the file name or exit the script if there is none or if a -h, -v
    or -? was given.
    """
    global VERBOSITY
    global LIMIT
    global FORCE_COLLECT_MODE
    global REPORT_MODE

    # Process command line arguments
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'd?hsvfrl:',('h','help','limit=','force','report'))
    except getopt.error, mystr:
        print('civiLDAPContact_OrganizationSync: %s\n' % mystr)
        print(__usage__)
        sys.exit(-1)
    for opt in optlist:
        if opt[0] == '-d':
            print __version__
            print
            print __doc__
            sys.exit(0)
        elif (opt[0] == '-h') or (opt[0] == '--h') or(opt[0] == '--help') \
          or (opt[0] == '-?'):
            print __usage__
            sys.exit(0)
        elif (opt[0] == '-s'):
            VERBOSITY=0
        elif (opt[0] == '-v'):
            VERBOSITY=2
        elif ((opt[0] == '-f') or (opt[0] == '--force')):
            FORCE_COLLECT_MODE = 1
        elif ((opt[0] == '-r') or (opt[0] == '--report')):
            REPORT_MODE = 1
        elif ((opt[0] == '-l') or (opt[0] == '--limit')):
            LIMIT = int(float(opt[1]))
    if (not args and not REPORT_MODE) :
        print("\nErreur: Vous devez passer en argument le chemin absolu vers le script civiLDAPContact_OrganizationSync.py.\n")
        print(__usage__)
        sys.exit(1)
    else:
        if REPORT_MODE:
            return ''
        else :
            return args[0]


def run():
    global MYSQL_HOST
    global MYSQL_DB_CIVICRM
    global MYSQL_CIVICRM_PREFIX
    global MYSQL_USER
    global MYSQL_PASS
    global VERBOSITY
    global FORCE_COLLECT_MODE
    global REPORT_MODE
    global CHILD_PATH 
    global ACCOUNT_CUSTOM
    global CONTACT_CUSTOM
    global db

    # getting args from command line
    CHILD_PATH = main_parseopts()

    #connect database
    try:
        printer('Connecting to MYSQL ...',2)
        db=MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER,passwd=MYSQL_PASS, db=MYSQL_DB_CIVICRM)
        db.query("SET NAMES 'utf8'");
        db.query("SET CHARACTER SET 'utf8'");
        printer('Success',2)
    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    TABLE_CONTACT = MYSQL_DB_CIVICRM + '.' + MYSQL_CIVICRM_PREFIX + 'contact'
    # create report 
    if REPORT_MODE:
        printer('### SYNC REPORT ###',1)
        c=db.cursor()
        sql = ('select '
          + " IF(is_deleted=0,'active ','deleted') as del,"
          + " IF( ldap_sync=0,'unitialized ',"
            + "IF(ldap_sync=1,'sync        ',"
            + "IF(ldap_sync=2,'sync running',"
            + "IF(ldap_sync=3,'need sync   ',"
            + "'unknown')))) as sync,"
          + 'count(*) as count '
          + ' from ' + TABLE_CONTACT
          + " where contact_type='Organization'"
          + ' group by del,ldap_sync '
          + ' order by ldap_sync ASC,del ASC;')
        c.execute(sql)
        res = c.fetchall()
        printer('db result ::' + str(res),2)
        if (None == res):
            c.close()
            printer('no info',1);
            sys.exit(0)
        printer('### Contact table',1)
        for stat in res:
            printer(' :: '.join(str(i) for i in stat)+ ' record(s)',1)
        c.close()
        sys.exit(0)

    # get contacts to sync
    try:
        printer('Find our desynchronised contacts in Database',1)
        c=db.cursor()
        # we need to detect active contacts not sync, inactive contacts which were sync and are not anymore (to delete theses contacts)
        # and as well in related association stable sor associated tables, we may have something previsouly recorded which is not related anymore
        # but we try to avoid runniong sync on uninitialised inactive relationships, as we do not have anything about it in ldap
        # and same for uninitialized active relationships on inactive contacts
        sql = ' from ' + TABLE_CONTACT
        sql = sql + ' where (' + TABLE_CONTACT + '.ldap_sync=0 '
        if FORCE_COLLECT_MODE:
            # try to add records with sync_status at 2 (running), from dead sync sessions
            sql = sql + ' OR ' + TABLE_CONTACT + '.ldap_sync=2 '
        sql = sql + ' OR ' + TABLE_CONTACT + '.ldap_sync=3) AND (' + TABLE_CONTACT + ".contact_type = 'Organization'"
        sql = sql + ')'
        countsql = 'select count(distinct(' + TABLE_CONTACT + '.id)) ' + sql
        sql = 'select distinct(' + TABLE_CONTACT + '.id) ' + sql
        if (0 != LIMIT):
            sql = sql + ' LIMIT ' + str(LIMIT)
        #print countsql
        c.execute(countsql)
        res = c.fetchone()
        total_sync = res[0]
        printer(str(total_sync) + ' records to sync',1)
        c.close()
        c=db.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        #print sql
        c.execute(sql)
        res = c.fetchall()
        printer('db result ::' + str(res),2)
        if (None == res):
            c.close()
            printer('nothing to do',1);
            sys.exit(0)
        c.close()
        contacts_list = res

    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    # launch civiLDAPContact_OrganizationSync.py for all theses records
    try:
        cpt=0
        for contact in contacts_list:
            cpt=cpt+1
            printer('synch contact id:' + str(contact['id'])+'==========['+str(cpt)+'/'+str(total_sync)+']==',1)
            if (0 == VERBOSITY) :
                verbosity = ' -s '
            elif (1==VERBOSITY):
                verbosity = ' '
            else :
                verbosity = ' -v '

            p=subprocess.Popen(CHILD_PATH+verbosity+str(contact['id']),shell=True)
            #sts = os.waitpid(p.pid, 0)
            p.wait()
            retcode = p.returncode
            if (retcode<0):
                printer('** child script terminated by signal ' + str(retcode),1);
            else:
                printer('child script returned signal' + str(retcode),2);
        printer ('synchro done for '+str(cpt)+' records!',1)
    except OSError, e:
        print 'Error launching individual contact synchro script'
        print e
        sys.exit(1)

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

if __name__=='__main__':
    run()
