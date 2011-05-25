#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
civiLDAPManage_UsersSync
====================
This script use civiLDAPUsersSync script to sync CiviCRM contact base on an OpenLDAP server. This one is the 'main' script.
It detects unsynced contacts and tell the other script to do the job.
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
Usage: civiLDAPManage_UsersSync.py [-h/-?/--h/--help] [-d] [-s/-v] i[-r/--report] [-f/--force] [-l/--limit LIMIT] PATH
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
# Here we need a user with read access on the MySQL Drupal database
MYSQL_USER = 'mysqluser'
MYSQL_PASS = 'mysqlpassword'
MYSQL_DB_DRUPAL = 'drupaldb'
MYSQL_DRUPAL_PREFIX = '' # something like like 'drupal_' or ''
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
        print('civiLDAPUsersSync: %s\n' % mystr)
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
        print("\nErreur: Vous devez passer en argument le chemin absolu vers le script civiLDAPUsersSync.py.\n")
        print(__usage__)
        sys.exit(1)
    else:
        if REPORT_MODE:
            return ''
        else :
            return args[0]


def run():
    global MYSQL_HOST
    global MYSQL_DRUPAL_PREFIX
    global MYSQL_DB_DRUPAL
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
        db=MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER,passwd=MYSQL_PASS,)
        db.query("SET NAMES 'utf8'");
        db.query("SET CHARACTER SET 'utf8'");
        printer('Success',2)
    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    USERS_TABLE = MYSQL_DB_DRUPAL + '.' + MYSQL_DRUPAL_PREFIX + 'users';
    # create report 
    if REPORT_MODE:
        printer('### SYNC REPORT ###',1)
        c=db.cursor()
        sql = ('select '
          + ' IF( ' + USERS_TABLE + ".ldap_sync=0 ,'unitialized ',"
          + ' IF( ' + USERS_TABLE + ".ldap_sync=1,'sync        ',"
          + ' IF( ' + USERS_TABLE + ".ldap_sync=2,'sync running',"
          + ' IF( ' + USERS_TABLE + ".ldap_sync=3,'need sync   ','unknown')))) as sync,"
          + ' count(*) as count'
          + ' from ' + USERS_TABLE 
          + ' where ' + USERS_TABLE + '.uid > 1'
          + ' group by ' + USERS_TABLE + '.ldap_sync '
          + ' order by ' + USERS_TABLE + '.ldap_sync ASC')
        sql = ('(' + sql + ') UNION ALL (' 
          + "select 'deleted     ', count(distinct(uid)) as count"
          + ' from ' + MYSQL_DB_DRUPAL + '.' + MYSQL_DRUPAL_PREFIX + 'ldap_sync_deleted_users'
          + ' WHERE uid>1'
          + ')')
        c.execute(sql)
        res = c.fetchall()
        printer('db result ::' + str(res),2)
        c2=db.cursor()
        if (None == res):
           c.close()
           #c2.close()
           printer('no info...',1);
           sys.exit(0)
        printer('### Contact table',1)
        for stat in res:
            printer(' :: '.join(str(i) for i in stat)+ ' record(s)',1)
        c.close()
        sys.exit(0)

    # get users to sync
    try:
        printer('Find our desynchronised users in Database',1)
        c=db.cursor()
        c2=db.cursor()
        sql = 'from ' + USERS_TABLE
        sql = sql + ' where (' + USERS_TABLE + ".ldap_sync=0"
        if FORCE_COLLECT_MODE:
            # try to add records with sync_status at 2 (running), from dead sync sessions
            sql = sql + ' OR ' + USERS_TABLE + '.ldap_sync=2'
        sql = sql + ' OR ' + USERS_TABLE + '.ldap_sync=3) AND (' + USERS_TABLE + '.uid > 1'
        sql = sql + ')'
        countsql = 'select count(distinct(' + USERS_TABLE + '.uid)) ' + sql
        sql = 'select distinct(' + USERS_TABLE + '.uid) ' + sql
        if (0 != LIMIT):
            sql = sql + ' LIMIT ' + str(LIMIT)
        # now add deleted users
        DELTABLE = MYSQL_DB_DRUPAL + '.' + MYSQL_DRUPAL_PREFIX + 'ldap_sync_deleted_users'
        sqldel = (' from ' + DELTABLE
          + ' WHERE ' + DELTABLE + '.uid>1')
        countsqldel = 'select count(distinct(' + DELTABLE + '.uid)) ' + sqldel
        sqldel = 'select distinct(' + DELTABLE + '.uid) ' + sqldel
        if (0 != LIMIT):
            sqldel = sqldel + ' LIMIT ' + str(LIMIT)
        #print countsql
        c.execute(countsql)
        c2.execute(countsqldel)
        res = c.fetchone()
        resdel = c2.fetchone()
        total_sync = res[0] + resdel[0]
        printer(str(total_sync) + ' records to sync',1)
        c.close()
        c2.close()
        c=db.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        c2=db.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        #print sql
        c.execute(sql)
        res = c.fetchall()
        c2.execute(sqldel)
        resdel = c2.fetchall()
        printer('db result unsync::' + str(res),2)
        printer('db result del::' + str(resdel),2)
        if (None == res and None==resdel):
            c.close()
            printer('nothing to do',1);
            sys.exit(0)
        c.close()
        users_list = res
        del_users_list = resdel

    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    # launch civiLDAPUsersSync.py for all theses records
    try:
        cpt=0
        for drupal_users in del_users_list:
            cpt=cpt+1
            printer('synch (del) user id:' + str(drupal_users['uid'])+'==========[' + str(cpt) + '/' + str(total_sync) + ']==',1)
            if (0 == VERBOSITY) :
                verbosity = ' -s '
            elif (1==VERBOSITY):
                verbosity = ' '
            else :
                verbosity = ' -v '
            delete = ' --remove-user '
            # this will remove a drupal user from the ldap user branch, this user does not exists anymore in Drupal
            p=subprocess.Popen(CHILD_PATH+verbosity+delete+str(drupal_users['uid']),shell=True)
            p.wait()
            retcode = p.returncode
            if (retcode<0):
                printer('** child script terminated by signal ' + str(retcode),1);
            else:
                printer('child script returned signal' + str(retcode),2);

        for users in users_list:
            cpt=cpt+1
            printer('synch user id:' + str(users['uid'])+'==========['+str(cpt)+'/'+str(total_sync)+']==',1)
            if (0 == VERBOSITY) :
                verbosity = ' -s '
            elif (1==VERBOSITY):
                verbosity = ' '
            else :
                verbosity = ' -v '

            p=subprocess.Popen(CHILD_PATH+verbosity+str(users['uid']),shell=True)
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
