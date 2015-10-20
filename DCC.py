#!/usr/bin/env python3

# external modules
from bs4 import BeautifulSoup
import pprint
import re
import requests
import getpass
import json
import os
import sys
from datetime import datetime
import time

# my modules
import Config as CF
import Tree
import FileSys

debug = False
DCC_URL = ''

# References for DCC login
# http://docs.python-requests.org/en/latest/user/quickstart/
# http://docushare.xerox.com/en-us/Help/prog/prog5.htm
# http://docushare.xerox.com/pdf/ds_whitepaper_Security.pdf
# http://customer.docushare.xerox.com/s.nl/ctype.KB/it.I/id.24908/KB.195/.f
# https://docushare.xerox.com/dsdn/dsweb/Get/Document-8931/DocuShare%20HTTP_XML%20Interface%20Protocol%20Specification.pdf

def add_docs_2_collections(s, docs, colls):
    # Syntax:	COPY / <handle>
    # HTTP Method:	POST
    # Function:	Copy the specified object.
    # Authorization: ANYONE with Manager access to <handle>.
    # Response Format: XML
    # docs - list of Document-XXXX handles
    # coll - list of Collection-XXXX handles
    # add the list of doc handles to the list of collections
    for c in colls:
        for d in docs:
            print('Adding ', d, ' to ', c)
            url = DCC_URL + "/dsweb/COPY/" + d
            headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "DESTINATION": c}
            r = s.post(url, headers=headers)
            if debug: print(r.text)
            
def change_owner(s, dochandle, userhandle):
    url = DCC_URL + "/dsweb/PROPPATCH/" + dochandle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop><entityowner><dsref handle="'''
    xml += userhandle
    xml += '''"/></entityowner></prop></set></propertyupdate>'''
    if debug: print(xml)
    r = s.post(url,data=xml,headers=headers)
    if debug: print(r.text)
    if debug: print(r.headers)
    print("Owner Change Status Code:", r.status_code)
    
    
def check_docs_in_coll(s, dl, cl):
    for c in cl:
        # get the list of documents in the collection
        
        cdl = list_obj_in_coll(s,c,Print=True,Jwrite=False,Depth='infinity',Type='Doc')

        for d in dl:
            #  print('testing ', d, ' in ', cdl)
            if not d in cdl:
                print(d, ' not found in ', c)
            else:
                print(d, ' found in ', c)
    
def dcc_move(s, handle, source, dest):
    # Syntax:	MOVE / <handle>
    # HTTP Method:	POST
    # Function:	Move the specified object.
    # Authorization:	ANYONE with Writer access to <handle>.
    # Response Format:	XML   
    # Because DocuShare allows objects to reside in more than one location at
    # the same time, the request header "SOURCE" must be provided to
    # disambiguate the MOVE request. Its value must be the handle of one of
    # the existing parents for <handle>.
    print('Moving ',handle,' from ', source,' to ', dest)
    url = DCC_URL + "/dsweb/MOVE/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "SOURCE": source, "DESTINATION": dest}
    r = s.post(url, headers=headers) 
    print(r.text)
    
def dcc_remove_doc_from_coll(s, handle, coll):
    """ Removes the location of the document from the collection
        handle - the document handle
        coll - the parent collection
    """
    # First find other collections where the document exists
    loc = prop_get(s, handle, InfoSet = 'Parents')
    incoll = False  # Flag to check that the document exists in the collection
    target = None # target should contain a valid target collection
    for l in loc:
        # Find another collection where the document exists that can be the destination
        if coll != l[0]:
            target = l[0]
        if coll == l[0]:
            incoll = True
    if incoll == True and target != None:
        print('Removing ', handle, ' from ', coll)
        dcc_move(s, handle,  coll, target)
    else:
        print('Failed to remove ', handle, ' from ', coll)
    
def file_download(s, handle, targetpath, filename):
    # Handle can be a Document-XXXXX, File-XXXXX or a Rendition-XXXXX
    url = DCC_URL + "/dsweb/GET/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
    r = s.post(url,headers=headers) 
    file = open(targetpath + filename,'wb')
    for chunk in r.iter_content(100000):
        file.write(chunk)
    file.close
    return(r) 
    
def file_download_html(url, cookies, outfile):
    # Writes html from url to outfile
    r = requests.get(url, cookies = cookies)
    webfile = open(CF.dccfilepath + outfile,'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close
    
def file_read_collection(coll):
    # Reads collection data from a .html file on disk
    htmlfile = '/Users/sroberts/Box Sync/Python/' + coll + '.html'
    fh=open(CF.dccfilepath + htmlfile,'r',encoding='utf-8').read()
    dom = BeautifulSoup(fh)
    clist = read_coll_cont(dom)
    return(clist)

def get_handle(url):
    #  Takes url such as 'https://docushare.tmt.org:443/File-501', returns 'Document-501'
    #  Replaces 'File' with 'Document'
    fileRegex = re.compile(r'File')
    handle = url.split('/')[-1]
    handle = fileRegex.sub('Document', handle)
    return(handle)  
    
def is_preferred_version(vd, fd):
    if fd['prefver'] == vd['dccver']:
        return True
    else:
        return False 

def list_obj_in_coll(s, collhandle, **kwargs):
    pflag = kwargs.get('Print', False)
    jflag = kwargs.get('Jwrite',False)
    depth = kwargs.get('Depth','infinity')
    type = kwargs.get('Type','Doc')
    writeprop = kwargs.get('WriteProp',False)
    
    if type == 'Doc':
        type_filter = 'Document-'
        file_ext = '_docs_' + depth + '.txt'
    elif type == 'Coll':
        type_filter = 'Collection-'
        file_ext = '_colls' + depth + '.txt'
    elif type == 'All':
        type_filter = '-'
        file_ext = '_allobjs' + depth + '.txt'
    else:
        sys.exit('type not found')

    fd = prop_get(s, collhandle, InfoSet = 'CollCont', Depth = depth, WriteProp = writeprop)
    objlist = []
    for f in fd:
        if type_filter in f['handle']:
            objlist.append(f['handle'])
            if pflag:
                print('Selected: ',f['handle'])
        else:
            if pflag:
                print('Other: ',f['handle'])
    if jflag:
        fh = open(CF.dccfilepath + collhandle + file_ext,'w')
        json.dump(objlist, fh)
        fh.close()
    return(objlist)
    
def login(url='',**kwargs):
    # kwargs options:
    # Site = 'Production' 
    # Site = 'Test'
    
    global DCC_URL
    
    if not url:
        if debug: print('Login: Url argument not supplied')
        site = kwargs.get('Site') 
        if site == 'Production':
            print('\nLogging in to DCC ***Production*** Site')
            DCC_URL = CF.dcc_url
            url = CF.dcc_url + CF.dcc_login
        elif site == 'Test':
            print('\nLogging in to DCC ***Test*** Site')
            DCC_URL = CF.dcctest_url          
            url = CF.dcctest_url + CF.dcc_login
        else:
            DCC_URL = url
            print('Login: site kwarg not understood: ',site)
            sys.exit(1)
    else:
        DCC_URL = url.replace('/dsweb/Login','')
        if debug: print('Login: Url supplied as :', url)
    
    print('URL for Docushare is: ',url)
    # See if secrets file exists and if so use credentials from there
    try:
        import secrets
        if debug: print('Login: secrets.pw: ',secrets.pw)
        if CF.dcc_url in url or site == 'Production':
            uname = secrets.pw['DCC']['login']
            pword = secrets.pw['DCC']['password']
        elif CF.dcctest_url in url or site == 'Test':
            uname = secrets.pw['DCCTest']['login']
            pword = secrets.pw['DCCTest']['password']
        else:
            print('Could not determine password from secrets file')
                
    except:
        uname = input("Enter TMT Docushare Username:")
        pword = getpass.getpass()
        
    dname = "DocuShare"
    xml="""<?xml version='1.0' ?><authorization> <username>""" \
    + uname + """</username><password><![CDATA[""" \
    + pword + """]]></password><domain>""" \
    + dname + """</domain></authorization>"""
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
    s = requests.Session()
    try:
        r = s.post(url,data=xml,headers=headers)
        r.raise_for_status()
        print('Login status code:', r.status_code)
    except:
        print("Unable to log in")
        print("Login status code:", r.status_code)
        exit(0)
        
    c = s.cookies
    if debug: print('Cookies:\n', c)
    if debug: print('DCC_URL = ', DCC_URL)    
    return s
    
def make_collection(s,parentColl, collName, collDesc):
    # Create a collection, return the handle
    url = DCC_URL + "/dsweb/MKCOL/" + parentColl
    
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
     
    xml1 = """<?xml version="1.0" ?><propertyupdate><set><prop><displayname><![CDATA["""
    xml2 = """]]></displayname><description>"""
    xml3 = """</description></prop></set></propertyupdate>"""
    xml = xml1 + collName + xml2 + collDesc + xml3   
    
    r = s.post(url,data=xml,headers=headers)
    print("make_collection status code:", r.status_code)    
#     print('')
#     print('\n',r.text)
#     print('\n',r.headers)
    
    handle = r.headers['docushare-handle']
    return(handle)  
    
def prop_get(s, handle, **kwargs):
    # kwargs options:
    #  Depth - Level to get Collection children information ('0', '1' or 'infinity')
    #       '0' returns information on Collection itself
    #       '1' and 'infinity' return information on Collection content
    #  InfoSet = Children - Collection Children
    #  InfoSet = CollData - Information about Collection
    #  InfoSet = CollCont - Information about Collection Content (See Depth) 
    #  InfoSet = DocBasic - Document basic information
    #  InfoSet = DocDate - Document last modified date
    #  InfoSet = Group - Group information
    #  InfoSet = Parents - Locations of documents or collections
    #  InfoSet = Perms - Document Permissions
    #  InfoSet = User - User information
    #  InfoSet = VerAll - All Version information
    #  RetDom - Return BeautifulSoup object rather than file data structure
    #  WriteProp = (True|False) - Write .html to disk?
    #  Print = (True|False) - Call print function on InfoSet?

    url = DCC_URL + "/dsweb/PROPFIND/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
    infoDic = { 'Children' : '<children/>',
                'CollCont' : '<title/><summary/><entityowner/><getlastmodified/>',    
                'CollData' : '<title/><summary/><keywords/><entityowner/><getlastmodified/>',
                'DocBasic':'<author/><handle/><document/><getlastmodified/><size/><summary/><entityowner/><keywords/>',
                'DocDate': '<getlastmodified/>',
                'Group': '<entityowner/><handle/><parents/><children/>',
                'Parents': '<parents/>',
                'Perms': '<private/><acl/>',
                'Summary' : '<summary/>',
                'Title': '<handle/>',
                'User': '<entityowner/><handle/><parents/>',
                'VerAll' : '<revision_comments/><title/><version_number/><parents/><handle/><entityowner/><getlastmodified/>',
                'Versions' : '<versions/><document_tree/>'}

    infoSet = kwargs.get('InfoSet','DocBasic')
    if debug: print('infoSet:',infoSet)
    writeRes = kwargs.get('WriteProp', False)
    retDom = kwargs.get('RetDom',False)
    depth = kwargs.get('Depth','0') 
    headers['Depth'] = depth
    printFlag = kwargs.get('Print', False)
    
    if infoSet == 'CollCont':
        fRoot = handle + '_' + infoSet + depth
    else:
        fRoot = handle + '_' + infoSet
        
    if debug: print('fRoot:', fRoot)
    
    if infoSet == 'DocDate':
        isCached = False
    else:
        [isCached, fd] = FileSys.check_cache_fd_json(s, handle, infoSet, fRoot)
        if debug: print('isCached:', isCached)
    
    if not isCached:
        if debug: print('Calling DCC API from prop_get: ',infoSet, handle)
        if infoSet in infoDic:
            xml = """<?xml version="1.0" ?><propfind><prop>""" + infoDic[infoSet] + """</prop></propfind>"""
            r = s.post(url,data=xml,headers=headers)
        else:
            print('Calling without XML')
            r = s.post(url,headers=headers)
        if writeRes:
            FileSys.file_write_props(r, fRoot)
        dom = BeautifulSoup(r.text)
        if retDom:
            return(dom)
        if infoSet in infoDic:        
            fd = prop_scrape(dom, infoSet)
            FileSys.file_write_json(fd, fRoot)

    if printFlag: 
        prop_print(infoSet,fd)
        
    return(fd)
    
def prop_print(infoSet, fd):
    if infoSet == 'DocBasic':
        print_doc_basic(fd)
    elif infoSet == 'DocDate':
        date = dom.getlastmodified.text
        print('Date: ', fd['date'])
    elif infoSet == 'Parents':
        print_parents(fd)
    elif infoSet == 'Children':
        print_children(fd)
    elif infoSet == 'VerAll':
        print_ver(fd)
    elif infoSet == 'Versions':
        print_versions(fd)
    elif infoSet == 'CollData':
        print_coll_data(fd)
    elif infoSet == 'CollCont':     
        print_coll_cont(fd)
    elif infoSet == 'Perms':
        print_perms(fd)
    elif infoSet == 'Title':
        print_title(fd)
    elif infoSet == 'Group':
        print_group(fd)
    elif infoSet == 'User':
        print_user(fd)

def prop_scrape(dom, infoSet):
    if infoSet == 'DocBasic':
        fd = read_doc_basic_data(dom)
    elif infoSet == 'DocDate':
        date = dom.getlastmodified.text
        fd = {'date':date}
    elif infoSet == 'Parents':
        fd = []
        for par in dom.find("parents").find_all("dsref"):
            fd.append([par['handle'],par.displayname.text])
    elif infoSet == 'Children':
        fd = []
        for par in dom.find("children").find_all("dsref"):
            fd.append([get_handle(par['handle']),par.displayname.text])
    elif infoSet == 'VerAll':
        fd = read_ver_data(dom)   
    elif infoSet == 'Versions':
        fd = read_versions(dom)   
    elif infoSet == 'CollData':
        fd = read_coll_data(dom)
    elif infoSet == 'CollCont':     
        fd = read_coll_cont(dom)
    elif infoSet == 'Perms':
        fd = read_perm(dom)
    elif infoSet == 'Title':
        fd = read_title(dom)
    elif infoSet == 'Group':
        fd = read_group(dom)
    elif infoSet == 'User':
        fd = read_user(dom)
    return(fd) 
    
def print_children(fd):
    print("\n\tChildren...")
    for c in fd:
        print("\t  [",c[0],"], \"", c[1], "\"", sep = "")

def print_coll_data(fd):
    # used for Depth = '0'
    print("\n\t*** Collection Handle", fd['handle'], "***\n")
    print("\tTitle: ", fd['title'])
    print("\tSummary: ", fd['summary'])
    print("\tKeywords: ", fd['keywords'])
    print("\tModified Date: ", fd['date'])
    print("\tOwner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
      
def print_coll_cont(clist):
# Used for depth of '1' or 'infinity'
    # pprint.pprint(clist)
    idx = 0
    for c in clist:
        if idx == 0:
            print("\n\tListing of: ",sep = "",end="")
            print_coll_cont_entry('',c)
            print("\n\tContents:")
        else: 
            print("\t  ",'%2d' % idx, ": ", sep="", end="")
            print_coll_cont_entry('    ',c)
            print("")
        idx += 1
       
def print_coll_cont_entry(indent,c):
    print("\t",indent,"[", c['name'][1], "], \"", c['name'][0], "\"", sep = "")
    print('\t\t',indent,"Summary: ", c['summary'], sep = "")
    print('\t\t',indent,"Last Modified: ", c['date'], sep = "")
    print('\t\t',indent,"Owner: [", c['owner'][2], "], [", c['owner'][1], "], \"", c['owner'][0], "\"", sep = "")
    
def print_group(fd):
    print("\n\tHandle: ", fd['handle'])
    print("\tName: ", fd['title'])
    print("\tOwner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print_parents(fd['parents'])
    print_children(fd['children'])

def print_doc_basic(fd):    
    print("\n\tDCC Title: ", fd['title'])
    print("\tTMT Document Number: ", fd['tmtnum'])
    print("\tDCC Document Handle/FileName: ", fd['handle'],", \"",fd['filename'],"\"",sep="")
    print("\tDCC Date: ", fd['date'])
    print("\tOwner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print("\tAuthor: ", fd['author'], sep="")
    print("\tKeywords: ", " \"", fd['keywords'], "\"", sep="")
    print("\tSize: ", fd['size'])
    
def print_doc_all(fd):
    print("\n** Document Entry", fd['handle'], "***\n")
    print("TMT Document Number: ", fd['tmtnum'])
    print("DCC Document Number/Name: ", fd['handle'],", \"",fd['title'],"\"",sep="")
    print("DCC Preferred Version: ", fd['prefver'])
    print("File Name: ", "\"",fd['filename'],"\"", sep = "")
    print("Modified Date: ", fd['date'])
    print("Owner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print("Author: ", fd['author'], sep="")
    print("Keywords: ", " \"", fd['keywords'], "\"", sep="")
    print("Last Modified: ", fd['date'])#     print_perms(fd['permissions'])
    print("\nLocations...")
    for loc in sorted(fd['locations'], key = lambda x: x[0]):
        print(loc[0],", \"",loc[1],"\"", sep="")
    print("\nVersions...")
    for ver in sorted(fd["versions"], key = lambda x: x[2], reverse = True ):
        print("Version:", ver[2], ", [", ver[0], "], [",ver[3], "], \"", ver[1], "\"", sep="")
    print("\n*** End Document Entry", fd['handle'], "***\n")
    
def print_locations(fd):
    print("\n\tLocations...")
    for loc in sorted(fd['locations'], key = lambda x: x[0]):
        print('\t',loc[0],", \"",loc[1],"\"", sep="")

def print_versions(fd):
    print("\n\tVersions...")
    for ver in sorted(fd["versions"], key = lambda x: x[2], reverse = True ):
        print("\tVersion:", ver[2], ", [", ver[0], "], [",ver[3], "], \"", ver[1], "\"", sep="")


def print_parents(fd):   
    print("\n\tParents...")
    for p in fd:
        print("\t  [",p[0],"], \"", p[1], "\"", sep = "") 
              
def print_perm(perm, **kwargs):
    print("\t[",perm["handle"],"]:\t","perms = ",sep="",end="")
    if "Search" in perm.keys():
        print("[Search]", end="")
    if "Read" in perm.keys():
        print("[Read]", end="")
    if "Write" in perm.keys():
       print("[Write]", end="")
    if "Manage" in perm.keys():
        print("[Manage]", end="")
    print(", \"",perm['name'],"\"",sep="",end="")
    if kwargs.get('LF',False):
        print('')

def print_perms(permlist):
    print("\n\tPermissions...")
    for perm in sorted(permlist['perms'], key = lambda x: x["handle"]):
        print_perm(perm)
        print("")    
    print('\tPrivate: ', permlist['private'])
        
def print_title(fd):
    print("\n\tHandle: ", fd['handle'])
    print("\tName: ", fd['title'])
    
def print_user(fd):
    print("\n\tHandle: ", fd['handle'])
    print("\tOwner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print_parents(fd['parents'])

def print_ver(fd):
    print("\n\t*** Version Entry", fd['dccver'], "***\n")
    print("\tVersion: ", fd['dccver'])
    print("\tVersion Number: ",fd['dccvernum'])
    print("\tVersion Comment: ", fd['vercomment'])
    print("\tVersion Owner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print("\tLast Modified: ", fd['date'])
    print("\n\tParent DCC Document Number: ", get_handle(fd['dccdoc']))
    print("\tParent Document Title:", "\"", fd['dcctitle'], "\"", sep = "")
    print("\n\t*** End Version Entry", fd['dccver'], "***\n")

def read_coll_cont(dom):
# Used for depth of '1' or 'infinity'
    clist = []
    for res in dom.find_all("response"):
        fd = {}
        fd['name'] = [res.title.text, get_handle(res.href.text)]
        fd['title'] = res.title.text
        fd['handle'] = get_handle(res.href.text)
        fd['owner-name'] = dom.entityowner.displayname.text
        fd['owner-username'] = dom.entityowner.username.text
        fd['owner-userid'] = dom.entityowner.dsref['handle']
        fd['owner'] = [fd['owner-name'], fd['owner-username'], fd['owner-userid']]
        fd['summary'] = res.summary.text
        fd['date'] = dom.getlastmodified.text
                   
        clist.append(fd)
    return(clist)
       
def read_coll_data(dom):
    # Applies to collection data for Depth = '0'
    fd = {}
    fd['handle'] = get_handle(dom.response.href.text)
    fd['title'] = dom.title.text
    fd['summary'] = dom.summary.text
    fd['keywords'] = dom.keywords.text
    fd['date'] = dom.getlastmodified.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    return(fd)
    
def read_doc_basic_data(dom):
    fd = {}
    fd['title'] = dom.displayname.text
    fd['handle'] = get_handle(dom.handle.dsref['handle'])
    fd['tmtnum'] = dom.summary.text
    fd['filename'] = dom.document.text
    fd['date'] = dom.getlastmodified.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    fd['author'] = dom.author.text
    fd['keywords'] = dom.keywords.text
    fd['size'] = int(dom.size.text)
    return(fd)

def read_doc_data(dom):
    # fill in file data dictionary
    fd = {}
    fd['title'] = dom.displayname.text
    fd['handle'] = get_handle(dom.href.text)
    fd['tmtnum'] = dom.summary.text

    fd['filename'] = dom.webdav_title.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    fd['author'] = dom.author.text
    fd['keywords'] = dom.keywords.text
    fd['date'] = dom.getlastmodified.text
    
    fd['locations'] = []
    colls = dom.find("parents").find_all("dsref")
    for coll in colls:
        fd['locations'].append([coll['handle'],coll.displayname.text])
        
    fd['versions'] = []        
    fd['prefver'] = dom.preferred_version.dsref['handle']
    vers = dom.find("versions").find_all("version")
    for ver in vers:
        fd['versions'].append([ver.dsref['handle'],ver.comment.text,ver.videntifier.text.zfill(2),ver.username.text])
        
    return(fd)
    
def read_versions(dom):
    fd = {}
    fd['versions'] = []        
    fd['prefver'] = dom.preferred_version.dsref['handle']
    vers = dom.find("versions").find_all("version")
    for ver in vers:
        fd['versions'].append([ver.dsref['handle'],ver.comment.text,ver.videntifier.text.zfill(2),ver.username.text])
    return(fd)

def read_locations(dom):
    fd = {}
    fd['locations'] = []
    colls = dom.find("parents").find_all("dsref")
    for coll in colls:
        fd['locations'].append([coll['handle'],coll.displayname.text])
    return(fd)
    
def read_group(dom):
    fd = {}
    fd['handle'] = dom.handle.dsref['handle']
    fd['title'] = dom.handle.displayname.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    
    fd['parents'] = []
    for par in dom.find("parents").find_all("dsref"):
        fd['parents'].append([par['handle'],par.displayname.text])
        
    fd['children'] = []
    for child in dom.find("children").find_all("dsref"):
        fd['children'].append([child['handle'], child.displayname.text])
    return(fd)
    
def read_perm(dom):
    fd = {}
    # Permissions
    perms = {}
    perms['perms'] = []

    perms['private'] = False
    try:
        if dom.private.text == '1':
            perms['private'] = True
    except:
        pass
    
    for p in dom.find_all("ace"):  
        try:     
            pentry = {}
            pentry["handle"] = p.dsref.get('handle')
            pentry["name"] = p.displayname.text
            if p.searchers != None:
                pentry["Search"] = True
            if p.readers != None:
                pentry["Read"] = True
            if p.writers != None:
                pentry["Write"] = True 
            if p.managers != None:
                pentry["Manage"] = True
            perms['perms'].append(pentry)  
        except:
            pass
    return(perms)
        
def read_title(dom):
    # fill in data dictionary
    fd = {}
    fd['title'] = dom.displayname.text
    fd['handle'] = get_handle(dom.handle.dsref['handle'])
    return(fd)
    
def read_user(dom):
    fd = {}
    fd['handle'] = dom.entityowner.dsref['handle']
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    fd['parents'] = []
    for par in dom.find("parents").find_all("dsref"):
        fd['parents'].append([par['handle'],par.displayname.text])
    return(fd)
    
def read_ver_data(dom):
    # fill in file data dictionary
    fd = {}
    fd['dccver'] = dom.handle.dsref["handle"]
    fd['dccdoc'] = get_handle(dom.find('parents').dsref["handle"])
    fd['dccvernum'] = dom.version_number.text
    fd['dcctitle'] = dom.title.text
    fd['vercomment'] = dom.revision_comments.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    fd['date'] = dom.getlastmodified.text
    return(fd)
    
def set_metadata(s, dochandle, **kwargs):

    keywords = kwargs.get('Keywords')
    summary = kwargs.get('Summary')
    displayname = kwargs.get('Title')
    description = kwargs.get('Description')
    
    url = DCC_URL + "/dsweb/PROPPATCH/" + dochandle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop>'''
    if keywords != None:
        xml += '''<keywords><![CDATA[''' + keywords + ''']]></keywords>'''
    if summary != None:
        xml += '''<summary><![CDATA[''' + summary + ''']]></summary>'''
    if displayname != None:
        xml += '''<displayname><![CDATA[''' + displayname + ''']]></displayname>'''
    if description != None:
        xml += '''<description><![CDATA[''' + description + ''']]></description>'''

    xml += '''</prop></set></propertyupdate>'''
    if debug: print(xml)
    r = s.post(url,data=xml,headers=headers)
    if debug: print(r.text)
    if debug: print(r.headers)
    print("Keywords Change Status Code:", r.status_code)
    
def set_private(s, handle, private_flag):
    # fd follows the permissions dictionary format
    
    url = DCC_URL + "/dsweb/PROPPATCH/" + handle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop>'''
    if private_flag == True:
        xml += '''<private>1</private>'''
    else:
        xml += '''<private></private>'''
    xml += '''</prop></set></propertyupdate>'''
    r = s.post(url,data=xml,headers=headers)
    print("Permission Change Status Code:", r.status_code)

def set_permissions(s,handle,permdata):
    # fd follows the permissions dictionary format
    
    if debug: print('\n\nPermdata:', permdata, '\n\n')
    url = DCC_URL + "/dsweb/PROPPATCH/" + handle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop><acl handle="''' 
    xml += handle
    xml += '''">'''
    for entry in permdata['perms']:
        read = entry.get('Read','False')
        write = entry.get('Write','False')
        manage = entry.get('Manage','False')
        
        xml += '''<ace><principal><dsref handle="'''
        xml += entry['handle']
        xml += '''"/></principal><grant>'''
        if read == True:
            xml += '''<readlinked/><readobject/><readhistory/>'''
        if write == True:
            xml += '''<writelinked/><writeobject/>'''
        if manage == True:
            xml += '''<manage/>'''
        if 'Collection' in handle:
            xml += '''</grant></ace>'''   
        if 'File' in handle or 'Document' in handle:
            xml += '''</grant><cascade/></ace>'''   
    xml += '''</acl>'''
#     if permdata['private'] == True:
#         xml += '''<private>1</private>'''
#     else:
#         xml += '''<private></private>'''
    xml += '''</prop></set></propertyupdate>'''
    if debug: print(xml)
    r = s.post(url,data=xml,headers=headers)
    print("Permission Change Status Code:", r.status_code)
    # Now write new permissions back to cache
    fd = prop_get(s, handle, InfoSet = 'Perms')


def test_change_owner():
    # Login to DCC
    s = login(Site = 'Production')
    collhandle = 'Collection-10892'
    dochandle = 'Document-27819'
    curr_owner = 'User-50'
    new_owner = 'User-1083'
    
    print('\n*** Currently ****')
    fd = prop_get(s, collhandle, InfoSet = 'CollData')
    print_coll_data(fd)
    
    fd = prop_get(s, dochandle, InfoSet = 'DocBasic')
    print_doc_basic(fd)
   
    print('\n*** Change Owner ****') 
    change_owner(s, collhandle, new_owner)
    
    fd = prop_get(s, collhandle, InfoSet = 'CollData')
    print_coll_data(fd)

    fd = prop_get(s, dochandle, InfoSet = 'DocBasic')
    print_doc_basic(fd)
    
    print('\n*** Change Back ****') 

    change_owner(s, collhandle, curr_owner)
    
    fd = prop_get(s, collhandle, InfoSet = 'CollData')
    print_coll_data(fd)
    
    fd = prop_get(s, dochandle, InfoSet = 'DocBasic')
    print_doc_basic(fd)

def test_version():
    # Login to DCC
    s = login(Site = 'Production')

    handle = 'Version-32465'
    fd = prop_get(s, handle, InfoSet = 'VerAll', WriteProp = True)
    print_ver(fd)
    

def test_props():
    # Login to DCC
    s = login(Site = 'Production')

    collhandle = 'Collection-7337'
    collhandle = 'Collection-10259'
    collhandle = 'Collection-286'
    collhandle = 'Collection-10259'

    verhandle = 'Version-49414'
    
    dochandle = 'Document-2688'
    dochandle = 'Document-27819'
    
    start = time.time()

    print('\nCall 2 DocBasic')
    fd = prop_get(s, dochandle, InfoSet = 'DocBasic', WriteProp = True, Print = True)

    print('\nCall 3 CollData')
    fd = prop_get(s, collhandle, InfoSet = 'CollData', WriteProp = True, Print = True)
 
    print('\nCall 4 CollCont Depth = 1')
    fd = prop_get(s, collhandle, InfoSet = 'CollCont', Depth = '1', WriteProp = True, Print = True)

    print('\nCall 5 CollCont Depth = infinity')
    fd = prop_get(s, collhandle, InfoSet = 'CollCont', Depth = 'infinity', WriteProp = True, Print = True)
 
    print('\nCall 6 Parents')
    fd = prop_get(s, collhandle, InfoSet = 'Parents', WriteProp = True, Print = True)

    print('\nCall 7 Children')
    fd = prop_get(s, collhandle, InfoSet = 'Children', Depth = 'infinity', WriteProp = True, Print = True)
    
    print('\nCall 8 CollData, Perms, Children')
    fd = prop_get(s, collhandle, InfoSet = 'CollData', WriteProp = True, Print = True)
    fd['permissions'] = prop_get(s, collhandle, InfoSet = 'Perms', WriteProp = True, Print = True)
    fd['children'] = prop_get(s, collhandle, InfoSet = 'Children', WriteProp = True, Print = True)

    print('\nCall 9 DocData, Perms, Children')
    fd = prop_get(s, dochandle, InfoSet = 'DocBasic', WriteProp = True, Print = True)
    fd['permissions'] = prop_get(s, dochandle, InfoSet = 'Perms', WriteProp = True, Print = True)    
    
    end = time.time()

    print('Execution time in seconds:', end - start)

def test_user_group():
    # Login to DCC
    s = login(Site = 'Production')

    grp = 'Group-666'
    fd = prop_get(s, grp, InfoSet = 'Group', Print = True, WriteProp = True)
    chandles = []
    for c in fd['children']:
        chandles.append(c[0])
    print(chandles)
    
def test_keywords():
    s = login(Site = 'Test')
    set_metadata(s,'Collection-25',
        Keywords = 'Keywords: TMTPublished',
        Summary = 'Summary: Scott Summary',
        Title = 'Title: Scott Collection',
        Description = 'Description: Scott Description')

def test_makecoll():
    s = login(Site = 'Test')
    make_collection(s, 'Collection-10', 'Python Made Collection', '')
    
def test_getall():
    s = login(Site = 'Production')    
    dochandle = 'Document-9946'
    prop_get(s,dochandle, InfoSet = 'None', WriteProp = True)


if __name__ == '__main__':
    print("Running module test code for",__file__)
#     test_props()
#     test_version()
#     test_change_owner()
#     test_user_group()
#     test_keywords()
#     test_makecoll()
    test_getall()
    


