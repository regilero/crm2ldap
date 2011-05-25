#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
civiLDAPContact_IndividualSync
====================
Sync one Civicrm individual contact to a OpenLDAP server record

see INSTALL.TXT file for long explanations

License: GNU GPL v2
(c) Makina Corpus - 2011
author : Régis Leroy - Guillaume Chéramy
"""
##########
# IMPORTS
import ldap
import ldap.modlist
import ldif
import MySQLdb
#import codecs
import sys
from time import strftime
import datetime
import string, os, getopt

#########
# DOCS
__version__="0.1"
__author__ = "regis.leroy@makina-corpus.org, guillaume.cheramy@makina-corpus.org"
__usage__ = """
Usage: civiLDAPContac_IndividualtSync.py [-h/-?/--h/--help] [-d] [-s/-v] ID
  **-h/-?/--help/--h**
    Show this little help
  **-d**
    Show the whole doc string of this script
  **-s**
    Silent mode
  **-v**
    Verbose mode
  **ID**
    ID is Civicrm contact's id 
"""

###########
# GLOBALS
########## BEGIN CUSTOM ZONE ##############################
# Adjust theses seetings to your install needs
MYSQL_HOST = 'localhost'
MYSQL_DB_CIVICRM = 'civicrmdb'
# Here we need a user with read access on the MySQL civicrm database
MYSQL_USER = 'mysqluser'
MYSQL_PASS = 'mysqlpassword'
MYSQL_CIVICRM_PREFIX = 'civicrm_' # something like like 'civicrm_' or ''

LDAP_HOST = '127.0.0.1'
# this user should get write access on the branch identified by CONTACT_BASE setting
LDAP_USER = 'cn=ldapuserwithwriteaccess,dc=example,dc=com'
LDAP_PASS = 'theldapuserpassword'
LDAP_BASE = 'dc=example,dc=com'
# here is the place where this script should be the master, all content in this area can be deleted by me
# and all changes there MUST come only from CIVICRM
# we'll put the contacts there. 
# This ou should already exists'
CONTACT_BASE = 'ou=ContactFromCivi,ou=People,'+LDAP_BASE

# list schemas that ldap contacts should use
# WARNING: mozillaAbPersonAlpha require an additional mozilla.schema and officePerson extension.schema
LDAP_SCHEMAS=[
    'person'
    ,'inetOrgPerson'
    ,'organizationalPerson'
    ,'mozillaAbPersonAlpha'
    ,'officePerson'
]

# list ldap fields you want on your ldap contacts
# all fields present in KEYS_MAPPING must be there before
LDAP_KEYS=[
    'objectClass'
    ,'uid'
    ,'dn'
    ,'cn'
    ,'givenName'
    ,'sn'
    ,'telephoneNumber'
    ,'homePhone'
    ,'title'
    ,'ou'
    ,'o'
    ,'physicalDeliveryOfficeName'
    ,'mail'
    ,'xmozillasecondemail'
    ,'facsimileTelephoneNumber'
    ,'pager'
    ,'mobile'
    ,'mozillaHomeStreet'
    ,'homePostalAddress'
    ,'mozillaHomeStreet2'
    ,'mozillaHomeLocalityName'
    ,'mozillaHomeState'
    ,'st'
    ,'mozillaHomePostalCode'
    ,'mozillaHomeCountryName'
    ,'street'
    ,'mozillaWorkStreet2'
    ,'l'
    ,'postalCode'
    ,'postalAddress'
    ,'countryName'
    ,'workurl'
    ,'homeurl'
    ,'birthyear'
    ,'description'
    ,'comment'
    ,'modifytimestamp'
    ,'mozillaHomeUrl'
    ,'homeURL'
]

# MAP Contact table fields to ldap fields, use none for ignore, and use lists -- ['elt1,'elt2'] -- for multiple fields mapping
# this one takes Outlook ldap mappings and thunderbird ones
# 'sql column : ldap attribute'
KEYS_MAPPING={
   'id':'uid'
   ,'contact_type':None
   ,'display_name':'displayName'
   ,'first_name':'givenName'
   ,'last_name':'sn'
   ,'label':None
   ,'job_title':'title'
   ,'organization_name':'o'
   ,'employer_id':None
   ,'is_deleted':None
   ,'ldap_sync':None
   ,'postal_code':'postalCode'
   ,'city':'l'
   ,'pays':'st'
   ,'work_phone':'telephoneNumber'
   ,'mobile_phone':'mobile'
   ,'fax_phone':'facsimileTelephoneNumber'
   ,'email':'mail'
   ,'url':['url','mozillaWorkUrl']
   ,'street_address': None
   ,'supplemental_address_1':None
   ,'supplemental_address_2':None
}

CONTACTINVERTED_MAPPING={
    'cn': ['first_name',[' '],'last_name']
   ,'postalAddress':['street_address',[' $ '],'supplemental_address_1',[' $ '],'supplemental_address_2']
}

# Do not touch theses ones, please
VERBOSITY = 2 #values are 0 (silent),1 (normal), 2(debug)
_REPTABLE = {}
SYNCID = 0
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

    # Process command line arguments
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'd?hsv',('h','help'))
    except getopt.error, mystr:
        print('civiLDAPContact_IndividualSync: %s\n' % mystr)
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
    if not args :
        print("\nErreur: donnez au moins un argument, faites -h par exemple.\n")
        print(__usage__)
        sys.exit(1)
    else:
        return args[0]

def print_ldap_result(res_type,res_data):
    if (res_type == ldap.RES_BIND) :
            print 'BIND result ::'
            print res_data
    elif (res_type== ldap.RES_SEARCH_ENTRY) :
            print 'SEARCH ENTRY result ::'
            print res_data
    elif (res_type== ldap.RES_SEARCH_REFERENCE) :
            print 'SEARCH REFERENCE result ::'
            print res_data
    elif (res_type== ldap.RES_SEARCH_RESULT) :
            print 'SEARCH result ::'
            print res_data
    elif (res_type== ldap.RES_MODIFY) :
            print 'MODIFY result ::'
            print res_data
    elif (res_type== ldap.RES_ADD) :
            print 'ADD result ::'
            print res_data
    elif (res_type== ldap.RES_DELETE) :
            print 'DELETE result ::'
            print res_data
    elif (res_type== ldap.RES_MODRDN) :
            print 'MODRN result ::'
            print res_data
    elif (res_type== ldap.RES_COMPARE) :
            print 'COMPARE result ::'
            print res_data
    else :
            print 'UNKNOW result ::'
            print res_data

def _fill_reptable():
    _corresp = [
        (u"A",  [0x00C0,0x00C1,0x00C2,0x00C3,0x00C4,0x00C5,0x0100,0x0102,0x0104]),
        (u"AE", [0x00C6]),
        (u"a",  [0x00E0,0x00E1,0x00E2,0x00E3,0x00E4,0x00E5,0x0101,0x0103,0x0105]),
        (u"ae", [0x00E6]),
        (u"C",  [0x00C7,0x0106,0x0108,0x010A,0x010C]),
        (u"c",  [0x00E7,0x0107,0x0109,0x010B,0x010D]),
        (u"D",  [0x00D0,0x010E,0x0110]),
        (u"d",  [0x00F0,0x010F,0x0111]),
        (u"E",  [0x00C8,0x00C9,0x00CA,0x00CB,0x0112,0x0114,0x0116,0x0118,0x011A]),
        (u"e",  [0x00E8,0x00E9,0x00EA,0x00EB,0x0113,0x0115,0x0117,0x0119,0x011B]),
        (u"G",  [0x011C,0x011E,0x0120,0x0122]),
        (u"g",  [0x011D,0x011F,0x0121,0x0123]),
        (u"H",  [0x0124,0x0126]),
        (u"h",  [0x0125,0x0127]),
        (u"I",  [0x00CC,0x00CD,0x00CE,0x00CF,0x0128,0x012A,0x012C,0x012E,0x0130]),
        (u"i",  [0x00EC,0x00ED,0x00EE,0x00EF,0x0129,0x012B,0x012D,0x012F,0x0131]),
        (u"IJ", [0x0132]),
        (u"ij", [0x0133]),
        (u"J",  [0x0134]),
        (u"j",  [0x0135]),
        (u"K",  [0x0136]),
        (u"k",  [0x0137,0x0138]),
        (u"L",  [0x0139,0x013B,0x013D,0x013F,0x0141]),
        (u"l",  [0x013A,0x013C,0x013E,0x0140,0x0142]),
        (u"N",  [0x00D1,0x0143,0x0145,0x0147,0x014A]),
        (u"n",  [0x00F1,0x0144,0x0146,0x0148,0x0149,0x014B]),
        (u"O",  [0x00D2,0x00D3,0x00D4,0x00D5,0x00D6,0x00D8,0x014C,0x014E,0x0150]),
        (u"o",  [0x00F2,0x00F3,0x00F4,0x00F5,0x00F6,0x00F8,0x014D,0x014F,0x0151]),
        (u"OE", [0x0152]),
        (u"oe", [0x0153]),
        (u"R",  [0x0154,0x0156,0x0158]),
        (u"r",  [0x0155,0x0157,0x0159]),
        (u"S",  [0x015A,0x015C,0x015E,0x0160]),
        (u"s",  [0x015B,0x015D,0x015F,0x01610,0x017F]),
        (u"T",  [0x0162,0x0164,0x0166]),
        (u"t",  [0x0163,0x0165,0x0167]),
        (u"U",  [0x00D9,0x00DA,0x00DB,0x00DC,0x0168,0x016A,0x016C,0x016E,0x0170,0x172]),
        (u"u",  [0x00F9,0x00FA,0x00FB,0x00FC,0x0169,0x016B,0x016D,0x016F,0x0171]),
        (u"W",  [0x0174]),
        (u"w",  [0x0175]),
        (u"Y",  [0x00DD,0x0176,0x0178]),
        (u"y",  [0x00FD,0x00FF,0x0177]),
        (u"Z",  [0x0179,0x017B,0x017D]),
        (u"z",  [0x017A,0x017C,0x017E])
        ]
    global _REPTABLE
    for repchar,codes in _corresp :
        for code in codes :
            _REPTABLE[code] = repchar

def suppression_diacritics(s) :
    """Suppression des accents et autres marques. from http://wikipython.flibuste.net/moin.py/JouerAvecUnicode

    @param s: le texte à nettoyer.
    @type s: str ou unicode
    @return: le texte nettoyé de ses marques diacritiques.
    @rtype: unicode
    """
    if isinstance(s,str) :
        s = unicode(s,"utf8","replace")
    return s.translate(_REPTABLE)

def suppression_diacritics_utf8(s) :
    """Suppression des accents et autres marques. from http://wikipython.flibuste.net/moin.py/JouerAvecUnicode

    @param s: le texte à nettoyer.
    @type s: str en utf8
    @return: le texte nettoyé de ses marques diacritiques.
    @rtype: unicode
    """
    return s.translate(_REPTABLE)

def affectLDAPField(targetkey,result,ldap_entries) :
    # specific requirements cleanups
    if ('mail' == targetkey) : 
        tmpresult = result.encode('utf-8','replace')
        printer('email before: '+tmpresult,2)
        result = suppression_diacritics(tmpresult)
        printer('email after: '+result,2)
    if (not ldap_entries[-1]['entry'].has_key(targetkey)):
        ldap_entries[-1]['entry'][targetkey] = []
    ldap_entries[-1]['entry'][targetkey].append(result.encode('utf-8','replace'))
    return ldap_entries

def filterTableContent(val):
    result = None
    if (isinstance(val,int) or isinstance(val,long)):
        result = str(val)
    else:
        if isinstance(val,datetime.datetime):
            result=str(val)
        else:
            if (None != val):
                if (type(val) == float):
                    result = val
                else:
                    result = val.decode('utf-8')
    return result

def run():
    global MYSQL_HOST
    global MYSQL_DB_CIVICRM
    global MYSQL_USER
    global MYSQL_PASS
    global MYSQL_CIVICRM_PREFIX
    global LDAP_HOST
    global LDAP_USER
    global LDAP_PASS
    global LDAP_BASE
    global CONTACT_BASE
    global LDAP_KEYS
    global LDAP_SCHEMAS
    global KEYS_MAPPING
    global CONTACTINVERTED_MAPPING
    global SYNCID
    global VERBOSITY
    global ACCOUNT_CUSTOM
    global CONTACT_CUSTOM
    global db

    # getting args from command line
    SYNCID = main_parseopts()

    #init replacement chars table
    _fill_reptable()

    #connect database
    try:
        printer('Connecting to MYSQL ...',2)
        dbc=MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER,passwd=MYSQL_PASS, db=MYSQL_DB_CIVICRM)
        dbc.query("SET NAMES 'utf8'");
        dbc.query("SET CHARACTER SET 'utf8'");
        printer('Success',2)
    except MySQLdb.MySQLError, e:
        print e
        sys.exit(1)

    # get contact to sync
    try:
        printer('Find our contact in Database with ID:' + SYNCID,1)
        c=dbc.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        sql = ('select '
          + MYSQL_CIVICRM_PREFIX + 'contact.id,'
          + MYSQL_CIVICRM_PREFIX + 'contact.contact_type,'
          + MYSQL_CIVICRM_PREFIX + 'contact.display_name,'
          + MYSQL_CIVICRM_PREFIX + 'contact.first_name,'
          + MYSQL_CIVICRM_PREFIX + 'contact.last_name,'
          + MYSQL_CIVICRM_PREFIX + 'option_value.label,'
          + MYSQL_CIVICRM_PREFIX + 'contact.job_title,'
          + MYSQL_CIVICRM_PREFIX + 'contact.organization_name,'
          + MYSQL_CIVICRM_PREFIX + 'contact.employer_id,'
          + MYSQL_CIVICRM_PREFIX + 'contact.is_deleted,'
          + MYSQL_CIVICRM_PREFIX + 'contact.ldap_sync,'
          + MYSQL_CIVICRM_PREFIX + 'address.street_address,'
          + MYSQL_CIVICRM_PREFIX + 'address.supplemental_address_1,'
          + MYSQL_CIVICRM_PREFIX + 'address.supplemental_address_2,'
          + MYSQL_CIVICRM_PREFIX + 'address.city,'
          + MYSQL_CIVICRM_PREFIX + 'address.postal_code,'
          + MYSQL_CIVICRM_PREFIX + 'country.name AS pays,'
          + MYSQL_CIVICRM_PREFIX + 'website.url'
          + ' from ' + MYSQL_CIVICRM_PREFIX + 'contact'
          + ' left join ' + MYSQL_CIVICRM_PREFIX + 'address on ' 
            + MYSQL_CIVICRM_PREFIX +'contact.id=' + MYSQL_CIVICRM_PREFIX + 'address.contact_id' 
          + ' left join ' + MYSQL_CIVICRM_PREFIX + 'option_value on ('
            + MYSQL_CIVICRM_PREFIX + 'contact.prefix_id=' + MYSQL_CIVICRM_PREFIX + "option_value.value AND option_group_id='6')"
          + ' left join ' + MYSQL_CIVICRM_PREFIX + 'country on ' 
            + MYSQL_CIVICRM_PREFIX + 'address.country_id=' + MYSQL_CIVICRM_PREFIX + 'country.id'
          + ' left join ' + MYSQL_CIVICRM_PREFIX + 'website on '
            + MYSQL_CIVICRM_PREFIX + 'contact.id=' + MYSQL_CIVICRM_PREFIX + 'website.contact_id'
          + ' left join ' + MYSQL_CIVICRM_PREFIX + 'uf_match on '
           + MYSQL_CIVICRM_PREFIX + 'uf_match.contact_id=' + MYSQL_CIVICRM_PREFIX + 'contact.id')

        c.execute(sql + " WHERE " + MYSQL_CIVICRM_PREFIX + "contact.contact_type='Individual' AND " + MYSQL_CIVICRM_PREFIX + "contact.id=%s",(SYNCID,))
        res = c.fetchone()
        if (None == res):
            c.close()
            print 'ID: '+SYNCID+' not found'
            sys.exit(1)
        printer('db result ::' + str(res),2)
        contact = res
        printer('Success',2)

        printer('Find additional infos for our contact ID email_addresse :' + SYNCID,1)
        c.close()
        c=dbc.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        c.execute("SELECT " + MYSQL_CIVICRM_PREFIX + "contact.id," + MYSQL_CIVICRM_PREFIX + "email.email"
          + " FROM " + MYSQL_CIVICRM_PREFIX + "contact"
          + " LEFT JOIN " + MYSQL_CIVICRM_PREFIX + "email ON " + MYSQL_CIVICRM_PREFIX + "contact.id=" + MYSQL_CIVICRM_PREFIX + "email.contact_id"
          + " WHERE " + MYSQL_CIVICRM_PREFIX + "contact.is_deleted = '0'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "email.is_primary='1'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "contact.id=%s",(SYNCID,))
        emails = c.fetchall()
        printer('db result ::' + str(emails),2)
        printer('Success',2)
        c.close()
        
        printer('Find additional infos for our contact ID phone_work :' + SYNCID,1)
        c.close()
        c=dbc.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        c.execute("SELECT " + MYSQL_CIVICRM_PREFIX + "contact.id," + MYSQL_CIVICRM_PREFIX + "phone.phone AS work_phone"
          + " FROM " + MYSQL_CIVICRM_PREFIX + "contact"
          + " LEFT JOIN " + MYSQL_CIVICRM_PREFIX + "phone ON " + MYSQL_CIVICRM_PREFIX + "contact.id=" + MYSQL_CIVICRM_PREFIX + "phone.contact_id"
          + " WHERE " + MYSQL_CIVICRM_PREFIX + "contact.is_deleted = '0'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id='1'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id IS NOT NULL"
          + " AND " + MYSQL_CIVICRM_PREFIX + "contact.id=%s",(SYNCID,))
        work_phone = c.fetchall()
        printer('db result ::' + str(work_phone),2)
        printer('Success',2)
        c.close()

        printer('Find additional infos for our contact ID phone_mobile :' + SYNCID,1)
        c.close()
        c=dbc.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        c.execute("SELECT " + MYSQL_CIVICRM_PREFIX + "contact.id," + MYSQL_CIVICRM_PREFIX + "phone.phone AS mobile_phone"
          + " FROM " + MYSQL_CIVICRM_PREFIX + "contact"
          + " LEFT JOIN " + MYSQL_CIVICRM_PREFIX + "phone ON " + MYSQL_CIVICRM_PREFIX + "contact.id=" + MYSQL_CIVICRM_PREFIX + "phone.contact_id"
          + " WHERE " + MYSQL_CIVICRM_PREFIX + "contact.is_deleted = '0'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id='2'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id IS NOT NULL"
          + " AND " + MYSQL_CIVICRM_PREFIX + "contact.id=%s",(SYNCID,))
        mobile_phone = c.fetchall()
        printer('db result ::' + str(mobile_phone),2)
        printer('Success',2)
        c.close()

        printer('Find additional infos for our contact ID phone_fax :' + SYNCID,1)
        c.close()
        c=dbc.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        c.execute("SELECT " + MYSQL_CIVICRM_PREFIX + "contact.id," + MYSQL_CIVICRM_PREFIX + "phone.phone AS fax_phone"
          + " FROM " + MYSQL_CIVICRM_PREFIX + "contact"
          + " LEFT JOIN " + MYSQL_CIVICRM_PREFIX + "phone ON " + MYSQL_CIVICRM_PREFIX + "contact.id=" + MYSQL_CIVICRM_PREFIX + "phone.contact_id"
          + " WHERE " + MYSQL_CIVICRM_PREFIX + "contact.is_deleted = '0'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id='3'"
          + " AND " + MYSQL_CIVICRM_PREFIX + "phone.phone_type_id IS NOT NULL"
          + " AND " + MYSQL_CIVICRM_PREFIX + "contact.id=%s",(SYNCID,))
        fax_phone = c.fetchall()
        printer('db result ::' + str(fax_phone),2)
        printer('Success',2)
        c.close()

    except MySQLdb.MySQLError, e:
        try:
            c.close
        except MySQLdb.MySQLError, e:
            print 'premature end'
        print e
        sys.exit(1)

    # mark DB record as sync starting in all related tables
    try:
        printer('mark ' + MYSQL_CIVICRM_PREFIX + 'contact '+ SYNCID+' as ldap_sync 2 -starting',2)
        dbc.query('BEGIN;');
        dbc.query('SET @DISABLE_TRIGGERS=1;')
        dbc.query('UPDATE ' + MYSQL_CIVICRM_PREFIX + 'contact set ldap_sync=2 where id="'+SYNCID+'";')
        dbc.query('SET @DISABLE_TRIGGERS=NULL;')
        dbc.query('COMMIT;')
    except MySQLdb.MySQLError, e:
        print 'mySQL error on recording starting sync state'
        print e
        sys.exit(1)

    # connect OpenLDAP
    try:
        printer('Connecting to LDAP ...',2)
        l = ldap.open(LDAP_HOST)
        l.protocol_version = ldap.VERSION3
        msgid=l.simple_bind(LDAP_USER, LDAP_PASS)
        #res_type,res_data = l.result(msgid,1,30)
        #print_ldap_result(res_type,res_data)
        printer('Success',2)
    except ldap.LDAPError, e:
        print 'LDAP Error : '
        print e
        sys.exit(1)

    # build the sync data
    ldif_writer=ldif.LDIFWriter(sys.stdout)
    ldap_entries = []
    i = 0
    ldap_entries.append({})
    ldap_entries[-1]['entry'] = {} 
    ldap_entries[-1]['entry']['objectClass'] = LDAP_SCHEMAS

    # handle MySQL fields
    for field, val in contact.iteritems():
        printer('FIELD:'+field,2)

        if (None == val or ''==val) : 
            printer('empty database field',2)
            continue
        result = filterTableContent(val)
        printer(result,2,'utf-8')

        # here we handle the UID, and we add the employer_id to get one contacts per company
        if 'id'==field:
            #BUGFIX: do not set empty value for deleted assocs, as the contact were maybe already created
            # with that assoc, and we need the complete id to delete him
            #if (contact['company_del']==0 and contact['assoc_del']==0):
            if (None != contact['employer_id']):
                employer_id = contact['employer_id']
            else :
                printer('DELETED ASSOC OR COMPANY',2)
                employer_id = ''
            result = result + '-' + str(employer_id)
            printer('setting dn entry for uid '+ result,2)
            ldap_entries[-1]['dn'] = 'uid=' + result + ','+ CONTACT_BASE

        target_key = KEYS_MAPPING[field]
        if (None == target_key):
            printer('empty mapping',2)
            continue
        if (isinstance(target_key,dict)):
            target_key=target_key['mapping']
            if (None == target_key):
                printer('empty mapping',2)
                continue
        if (isinstance(target_key,list)):
            for tg in target_key:
                ldap_entries = affectLDAPField(tg,result,ldap_entries)
        else:
            ldap_entries = affectLDAPField(target_key,result,ldap_entries)
        i = i+1

    # handle emails for this contact
    for emailrow in emails:
        printer('FIELDS EMAIL',2)
        result = filterTableContent(emailrow['email'])
        if (None == result) : 
            printer('empty database field',2)
            continue
        target_key = KEYS_MAPPING['email']
        if (None == target_key):
            printer('empty mapping',2)
            continue
        if (isinstance(target_key,list)):
            for tg in target_key:
                ldap_entries = affectLDAPField(tg,result,ldap_entries)
        else:
            ldap_entries = affectLDAPField(target_key,result,ldap_entries)

   # handle phone_work for this contact
    for twork in work_phone:
        printer('FIELDS PHONE_WORK',2)
        result = filterTableContent(twork['work_phone'])
        if (None == result) : 
            printer('empty database field',2)
            continue
        target_key = KEYS_MAPPING['work_phone']
        if (None == target_key):
            printer('empty mapping',2)
            continue
        if (isinstance(target_key,list)):
            for tg in target_key:
                ldap_entries = affectLDAPField(tg,result,ldap_entries)
        else:
            ldap_entries = affectLDAPField(target_key,result,ldap_entries)

   # handle phone_mobile for this contact
    for tmobile in mobile_phone:
        printer('FIELDS PHONE_MOBILE',2)
        result = filterTableContent(tmobile['mobile_phone'])
        if (None == result) : 
            printer('empty database field',2)
            continue
        target_key = KEYS_MAPPING['mobile_phone']
        if (None == target_key):
            printer('empty mapping',2)
            continue
        if (isinstance(target_key,list)):
            for tg in target_key:
                ldap_entries = affectLDAPField(tg,result,ldap_entries)
        else:
            ldap_entries = affectLDAPField(target_key,result,ldap_entries)

   # handle phone_fax for this contact
    for tfax in fax_phone:
        printer('FIELDS PHONE_FAX',2)
        result = filterTableContent(tfax['fax_phone'])
        if (None == result) : 
            printer('empty database field',2)
            continue
        target_key = KEYS_MAPPING['fax_phone']
        if (None == target_key):
            printer('empty mapping',2)
            continue
        if (isinstance(target_key,list)):
            for tg in target_key:
                ldap_entries = affectLDAPField(tg,result,ldap_entries)
        else:
            ldap_entries = affectLDAPField(target_key,result,ldap_entries)


    # handle inverted mapping for contact table (composite fields)
    # TODO: separator should be a list with 'value' and 'is_separator' keys (the field[0] here)
    for target_key,val in CONTACTINVERTED_MAPPING.iteritems() :
        if target_key in LDAP_KEYS:
            final = ''
            value = None
            separator = ''
            if isinstance(val,list):
                for field in val:
                    if isinstance(field,list):
                        # that's a string, not a field
                        if (None != value):
                            separator = field[0]
                            value = None
                    else:
                        #that's a field of contact
                        value = filterTableContent(contact[field])
                    if (None != value):
                        final = final + separator + value
            if ('' != final):
                ldap_entries = affectLDAPField(target_key,final.lstrip(),ldap_entries)
        else:
            printer('error in inverted mapping target key ' + target_key + ' is not in LDAP_KEYS!',1)

    if (VERBOSITY > 1):
        # show what we have
        for entry in ldap_entries:
            print ' ################################################### '
            printer(entry['dn'],2,'utf-8')
            my_entry = entry['entry']
            for key in LDAP_KEYS:
                if key in my_entry:
                    printer(key + '::' + str(my_entry[key]),2,'utf-8')

    # now SYNC our data 
    try:
        for entry in ldap_entries:
            #INSERTION
            modlist = ldap.modlist.addModlist(entry['entry'])
            #print modlist
            try:
                # verify this is not a deleted contact
                if (0 != contact['is_deleted']) :
                    try:
                        printer('deleting ' + entry['dn'],1)
                        msgid = l.delete_s(entry['dn'])
                    except ldap.NO_SUCH_OBJECT:
                        #do nothing
                        printer("in fact he wasn't there ",2)
                else:
                    printer('* adding ' + entry['dn'],1)
                    msgid = l.add_s(entry['dn'],modlist)
            except ldap.ALREADY_EXISTS, e:
                printer('deleting ' + entry['dn'],1)
                msgid = l.delete_s(entry['dn'])
                printer('re-adding ' + entry['dn'],1)
                msgid = l.add_s(entry['dn'],modlist)
                continue
    except ldap.LDAPError, e:
        printer (' On Error, debug:' + str(modlist),1)
        print 'LDAP Error : '
        print e
        sys.exit(1)

    try:
        printer('record sync is done',1)
        printer('mark ' + MYSQL_CIVICRM_PREFIX + 'contact '+ SYNCID+' as ldap_sync 1 -success',2)
        dbc.query('BEGIN;')
        dbc.query('SET @DISABLE_TRIGGERS="1";')
        dbc.query('UPDATE ' + MYSQL_CIVICRM_PREFIX + 'contact set ldap_sync=1 where id="'+SYNCID+'";')
        dbc.query('SET @DISABLE_TRIGGERS=NULL;')
        dbc.query('COMMIT;')
    except MySQLdb.MySQLError, e:
        print 'mySQL error on recording successfull sync state'
        print e
        sys.exit(1)


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

if __name__=='__main__':
    run()
