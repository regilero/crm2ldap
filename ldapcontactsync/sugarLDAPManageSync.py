#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
sugarLDAPManageSync
====================
This script use sugarLDAPContactSync script to sync SugraCRM contact base on an OpenLDAP server. This one is the 'main' script.
He detects unsynced contacts and tell the other script to do the job.
By giving him some args you can limit number of contacts treated.
This script includes as well a --report option to get some sync status stats report

see INSTALL.TXT file for long explanations

License: GNU GPL v2
(c) Makina Corpus - 2009
author : Régis Leroy
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
__version__="0.9"
__author__ = "regis.leroy@makina-corpus.org"
__usage__ = """
Usage: sugarLDAPManageSync.py [-h/-?/--h/--help] [-d] [-s/-v] i[-r/--report] [-f/--force] [-l/--limit LIMIT] PATH
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
MYSQL_DB = 'sugarcrm'
MYSQL_USER = 'root'
MYSQL_PASS = 'hererootpasswordformysql'
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
        print('sugarLDAPContactSync: %s\n' % mystr)
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
        print("\nErreur: Vous devez passer en argument le chemin absolu vers le script sugarLDAPContactSync.py.\n")
        print(__usage__)
        sys.exit(1)
    else:
        if REPORT_MODE:
            return ''
        else :
            return args[0]

def detect_custom_tables():
    global ACCOUNT_CUSTOM
    global CONTACT_CUSTOM
    global db
    try:
        printer('Test presence of custom tables',1)
        ACCOUNT_CUSTOM = False
        CONTACT_CUSTOM = False
        c=db.cursor()
        sql = """SHOW TABLES LIKE '%_cstm'"""
        c.execute(sql)
        res = c.fetchall()
        printer('db result ::' + str(res),2)
        if (None == res):
            printer('no custom tables',1)
        else:
            for cstm in res:
                if (cstm[0]=='accounts_cstm'):
                    ACCOUNT_CUSTOM = True
                    printer('accounts_cstm found',1)
                elif (cstm[0]=='contacts_cstm'):
                    CONTACT_CUSTOM = True
                    printer('contacts_cstm found',1)
        c.close()


    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

def run():
    global MYSQL_HOST
    global MYSQL_DB
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
        db=MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER,passwd=MYSQL_PASS, db=MYSQL_DB)
        db.query("SET NAMES 'utf8'");
        db.query("SET CHARACTER SET 'utf8'");
        printer('Success',2)
    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    detect_custom_tables()

    if REPORT_MODE:
        printer('### SYNC REPORT ###',1)
        c=db.cursor()
        sql = """select 
        IF(deleted=0,'active ','deleted') as del
        ,IF(ldap_sync=0,'unitialized ',IF(ldap_sync=1,'sync        ',IF(ldap_sync=2,'sync running',IF(ldap_sync=3,'need sync   ','unknown')))) as sync
        ,count(*) as count 
        from contacts 
        group by deleted,ldap_sync 
        order by ldap_sync ASC,deleted ASC;
        """
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

        if (CONTACT_CUSTOM):
            c=db.cursor()
            sql = """select
IF(contacts_cstm.ldap_sync=0,'unitialized ',
    IF(contacts_cstm.ldap_sync=1,'sync        ',
      IF(contacts_cstm.ldap_sync=2,'sync running',
        IF(contacts_cstm.ldap_sync=3,'need sync   ','unknown')))) as sync
,count(*) as count 
from contacts_cstm 
inner join contacts on contacts_cstm.id_c=contacts.id 
where contacts.deleted=0
group by contacts_cstm.ldap_sync 
order by contacts_cstm.ldap_sync ASC;
            """
            c.execute(sql)
            res = c.fetchall()
            printer('db result ::' + str(res),2)
            if (None == res):
                c.close()
                printer('no info',1);
                sys.exit(0)
            printer('### Contact Custom table: for active contacts',1)
            for stat in res:
                printer(' :: '.join(str(i) for i in stat)+ ' record(s)',1)
            c.close()

        c=db.cursor()
        sql = """select 
        IF(accounts.deleted=0,'active ','deleted') as del
        ,IF(ac.deleted=0,'join active ','join deleted') as joindel
        ,IF(accounts.ldap_sync=0,'unitialized ',
            IF(accounts.ldap_sync=1,'sync        ',
                IF(accounts.ldap_sync=2,'sync running',
                    IF(accounts.ldap_sync=3,'need sync   ','unknown')))) as sync
        ,IF(ac.ldap_sync=0,'join unitialized ',
            IF(ac.ldap_sync=1,'join sync        ',
                IF(ac.ldap_sync=2,'join sync running',
                    IF(ac.ldap_sync=3,'join need sync   ','unknown')))) as joinsync
        ,count(*) as count 
        from accounts 
        left join accounts_contacts ac on ac.account_id = accounts.id
        inner join contacts c on c.id = ac.contact_id
        where c.deleted=0
        group by accounts.deleted,ac.deleted,accounts.ldap_sync,ac.ldap_sync
        order by accounts.ldap_sync ASC,accounts.deleted;
        """
        c.execute(sql)
        res = c.fetchall()
        printer('db result ::' + str(res),2)
        if (None == res):
            c.close()
            printer('no info',1);
            sys.exit(0)
        printer('### Account table: for active contacts',1)
        for stat in res:
            printer(' :: '.join(str(i) for i in stat)+ ' record(s)',1)
        c.close()
        if (ACCOUNT_CUSTOM):
            # TODO: build this query as well
            printer('### Account Custom table: for active contacts',1)
            printer('TODO',1)

        printer('bye',1)
        sys.exit(0)

    # get contacts to sync
    try:
        printer('Find our desynchronised contacts in Database',1)
        c=db.cursor()
        # we need to detect active contacts not sync, inactive contacts which were sync and are not anymore (to delete theses contacts)
        # and as well in related association stable sor associated tables, we may have something previsouly recorded which is not related anymore
        # but we try to avoid runniong sync on uninitialised inactive relationships, as we do not have anything about it in ldap
        # and same for uninitialized active relationships on inactive contacts
        sql = """from contacts 
left join accounts_contacts on contacts.id=accounts_contacts.contact_id
left join accounts on accounts_contacts.account_id=accounts.id
left join `email_addr_bean_rel` on `contacts`.`id`=`email_addr_bean_rel`.`bean_id` 
left join `email_addresses` on `email_addr_bean_rel`.`email_address_id`=`email_addresses`.`id`"""
        if (CONTACT_CUSTOM):
            sql = sql + " left join `contacts_cstm` on `contacts`.`id`=`contacts_cstm`.`id_c` "
        if (ACCOUNT_CUSTOM):
            sql = sql + " left join `accounts_cstm` on `accounts`.`id`=`accounts_cstm`.`id_c` "
        sql = sql + " where (`contacts`.`ldap_sync`=0 "
        if FORCE_COLLECT_MODE:
            # try to add records with sync_status at 2 (running), from dead sync sessions
            sql = sql + " or `contacts`.`ldap_sync`=2 "
        sql = sql + """ or `contacts`.`ldap_sync`=3)
or (
	(`contacts`.`deleted`=0 ) and (
		(`accounts_contacts`.`ldap_sync`=0 and `accounts_contacts`.`deleted`=0)
		or (`accounts_contacts`.`ldap_sync`=3)
		or (`accounts`.`ldap_sync`=0 and `accounts`.`deleted`=0)
		or (`accounts`.`ldap_sync`=3)
		or (`email_addr_bean_rel`.`ldap_sync`=0 and `email_addr_bean_rel`.`deleted`=0)
		or (`email_addr_bean_rel`.`ldap_sync`=3)
		or (`email_addresses`.`ldap_sync`=0 and `email_addresses`.`deleted`=0)
		or (`email_addresses`.`ldap_sync`=3)"""
        if (CONTACT_CUSTOM):
		    sql = sql + """
            or (`contacts_cstm`.`ldap_sync`=0)
    		or (`contacts_cstm`.`ldap_sync`=3)"""
        if (ACCOUNT_CUSTOM):
            sql = sql + """
    		or (`accounts_cstm`.`ldap_sync`=0)
	    	or (`accounts_cstm`.`ldap_sync`=3)"""
        sql = sql + "))"
        if FORCE_COLLECT_MODE:
            # try to add records with sync_status at 2 (running), from dead sync sessions
            sql = sql + """ 
or (`accounts_contacts`.`ldap_sync`=2)
or (`accounts`.`ldap_sync`=2)
or (`email_addr_bean_rel`.`ldap_sync`=2)
or (`email_addresses`.`ldap_sync`=2)"""
        if (CONTACT_CUSTOM):
            sql = sql + " or (`contacts_cstm`.`ldap_sync`=2) "
        if (ACCOUNT_CUSTOM):
            sql = sql + " or (`accounts_cstm`.`ldap_sync`=2) "
        countsql = "select count(distinct(contacts.id)) " + sql
        sql = "select distinct(contacts.id) " + sql
        if (0 != LIMIT):
            sql = sql + " LIMIT " + str(LIMIT)
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

    # launch sugarLDAPContactSync.py for all theses records
    try:
        cpt=0
        for contact in contacts_list:
            cpt=cpt+1
            printer('synch contact id:' + contact['id']+'==========['+str(cpt)+'/'+str(total_sync)+']==',1)
            if (0 == VERBOSITY) :
                verbosity = ' -s '
            elif (1==VERBOSITY):
                verbosity = ' '
            else :
                verbosity = ' -v '

            p=subprocess.Popen(CHILD_PATH+'/sugarLDAPContactSync.py '+verbosity+contact['id'],shell=True)
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

