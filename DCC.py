#!/usr/bin/env python3

# external modules
from bs4 import BeautifulSoup
import pprint
import re
import requests
import getpass
import json

# my modules
import config as cf

# References for DCC login
# http://docs.python-requests.org/en/latest/user/quickstart/
# http://docushare.xerox.com/en-us/Help/prog/prog5.htm
# http://docushare.xerox.com/pdf/ds_whitepaper_Security.pdf
# http://customer.docushare.xerox.com/s.nl/ctype.KB/it.I/id.24908/KB.195/.f
# https://docushare.xerox.com/dsdn/dsweb/Get/Document-8931/DocuShare%20HTTP_XML%20Interface%20Protocol%20Specification.pdf


def login(url):
    # See if secrets file exists and if so use credentials from there
    try:
        import secrets
        uname = secrets.pw['DCC']['login']
        pword = secrets.pw['DCC']['password']
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
        print('Status code:', r.status_code)
    except:
        print("Unable to log in")
        print("Status Code:", r.status_code)
#         print('headers:\n', r.headers)
#         print('request headers:\n',r.request.headers)
        exit(0)
        
    c = s.cookies
    # print('Cookies:\n', c)
    return s
    
def get_yn(question):
    ans = ''
    while (ans.upper() != 'Y') and (ans.upper() != 'N'):
        print(question,end="")
        ans = input()
    if ans.upper() == 'Y':
        return True
    return False

def get_locations(s, handle):
    # Get all the locations for a document or a collection
    url = cf.dcc_url + "/dsweb/PROPFIND/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
    xml = """<?xml version="1.0" ?>
        <propfind>
            <prop>
                <parents/> 
            </prop>
        </propfind>"""     
    r = s.post(url,data=xml,headers=headers)  # Gets limited data
    dom = BeautifulSoup(r.text)
    colls = dom.find("parents").find_all("dsref")
    locations = []
    for coll in colls:
        locations.append([coll['handle'],coll.displayname.text])
    return locations
    
def get_collections_in_collection(s, coll):
    c_handles = dcc_get_coll_handles(s, coll)
    colllist = []
    for c in c_handles:
        if 'Collection-' in c:
            print('Collection: ', c) 
            colllist.append(c)
        else:
            print('Other: ', c)
    fh = open(cf.dccfilepath + coll + '_colls.txt','w')
    json.dump(colllist, fh)
    fh.close()
    return colllist    
    
def get_files_in_collection(s, coll):
    c_handles = dcc_get_coll_handles(s, coll)
    doclist = []
    for c in c_handles:
        if 'Document-' in c:
            print('Document: ', c) 
            doclist.append(c)
        else:
            print('Other: ', c)
    fh = open(cf.dccfilepath + coll + '_docs.txt','w')
    json.dump(doclist, fh)
    fh.close()
    return doclist

def prop_find(s, target):
    # POST /dscgi/ds.py/PROPFIND/Collection-49 HTTP/1.1
    # Host: docushare.xerox.com
    # Accept: text/xml
    # Content-Type: text/xml
    # Content-Length: xxxx
    #
    # A client may submit a Depth header with a value of "0", "1", or
    # "infinity". The depth input only applies to container objects
    # and will be ignored when given for non-container objects.
    # Clients should not supply a depth for non-container objects. The
    # depth value indicates whether the request is to be applied only
    # to the object identified by <handle> (depth=0), to the object
    # and its immediate children (depth=1), or to the object and all
    # its progeny (depth=infinity). When a depth value is not
    # provided, a value of inifinity will be assumed.
    
    url = cf.dcc_url + "/dsweb/PROPFIND/" + target
    # See if it is a collection
    if url.find('Collection') >= 0:
        headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "Depth":"infinity"}  

        xml = """<?xml version="1.0" ?>
            <propfind>
                <prop>
                    <displayname/><summary/><entityowner/><getcontenttype/><parents/> 
                </prop>
            </propfind>"""     
        r = s.post(url,data=xml,headers=headers)  # Gets limited data
    # Otherwise it's a Version or a Document and we don't use the xml string
    else: 
        headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
        r = s.post(url,headers=headers)     # Gets all data
    return(r)
    
def dom_prop_find(s, target):
    r = prop_find(s, target)
    # Need to add flag to turn on / off writing to file
    webfile = open(cf.dccfilepath + target+".html",'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close
    dom = BeautifulSoup(r.text)
    return dom

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
    url = cf.dcc_url + "/dsweb/MOVE/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "SOURCE": source, "DESTINATION": dest}
    r = s.post(url, headers=headers) 
    print(r.text)
    
def dcc_remove_doc_from_coll(s, handle, coll):
    # Find other collections where the document exists
    loc = get_locations(s, handle)
    incoll = False  # Flag to check that the document exists in the collection
    target = None # target should contains a valid target collection
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
            url = cf.dcc_url + "/dsweb/COPY/" + d
            headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "DESTINATION": c}
            r = s.post(url, headers=headers)
            print(r.text)
            
            
def download_html(url, cookies, outfile):
    # Writes html from url to outfile
    r = requests.get(url, cookies = cookies)
    webfile = open(cf.dccfilepath + outfile,'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close

def read_dcc_doc_data(dom):
    # fill in file data dictionary
    fd = {}
    fd['dccnum'] = get_handle(dom.acl['handle'])
    fd['prefver'] = dom.preferred_version.dsref['handle']
    fd['tmtnum'] = dom.summary.text
    fd['dccname'] = dom.displayname.text
    fd['filename'] = dom.webdav_title.text
    fd['modified'] = dom.getlastmodified.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    fd['keywords'] = dom.keywords.text
    fd['date'] = dom.getlastmodified.text
    fd['locations'] = []
    fd['versions'] = []
    colls = dom.find("parents").find_all("dsref")
    for coll in colls:
        fd['locations'].append([coll['handle'],coll.displayname.text])
    vers = dom.find("versions").find_all("version")
    for ver in vers:
        fd['versions'].append([ver.dsref['handle'],ver.comment.text,ver.videntifier.text.zfill(2),ver.username.text])
    # pprint.pprint(fd['versions'])
    # Permissions
    perms = []
    for p in dom.find_all("ace"):       
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
        perms.append(pentry)  
    fd["permissions"] = perms
    return(fd)

def print_doc_info(fd):
    print("\n\n*** Document Entry", fd['dccnum'], "***\n")
    print("TMT Document Number: ", fd['tmtnum'])
    print("DCC Document Number/Name: ", fd['dccnum'],", \"",fd['dccname'],"\"",sep="")
    print("DCC Preferred Version: ", fd['prefver'])
    print("File Name: ", "\"",fd['filename'],"\"", sep = "")
    print("Modified Date: ", fd['modified'])
    print("Owner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print("Keywords: ", " \"", fd['keywords'], "\"", sep="")
    print("Last Modified: ", fd['date'])
    print("\nPermissions...")
    for perm in sorted(fd["permissions"], key = lambda x: x["handle"]):
        print("[",perm["handle"],"]:\t","perms = ",sep="",end="")
        if "Search" in perm.keys():
            print("[Search]", end="")
        if "Read" in perm.keys():
            print("[Read]", end="")
        if "Write" in perm.keys():
           print("[Write]", end="")
        if "Manage" in perm.keys():
            print("[Manage]", end="")
        print(", \"",perm['name'],"\"",sep="")
    print("\nLocations...")
    for loc in sorted(fd['locations'], key = lambda x: x[0]):
        print(loc[0],", \"",loc[1],"\"", sep="")
    print("\nVersions...")
    for ver in sorted(fd["versions"], key = lambda x: x[2], reverse = True ):
        print("Version:", ver[2], ", [", ver[0], "], [",ver[3], "], \"", ver[1], "\"", sep="")
    print("\n*** End Document Entry", fd['dccnum'], "***\n")

def read_dcc_ver_data(dom):
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
    
def print_ver_info(fd):
    print("\n\n*** Version Entry", fd['dccver'], "***\n")
    print("Version: ", fd['dccver'])
    print("Version Number: ",fd['dccvernum'])
    print("Version Comment: ", fd['vercomment'])
    print("Version Owner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
    print("Last Modified: ", fd['date'])
    print("\nParent DCC Document Number: ", get_handle(fd['dccdoc']))
    print("Parent Document Title:", "\"", fd['dcctitle'], "\"", sep = "")
    print("\n*** End Version Entry", fd['dccver'], "***\n")
    
def is_preferred_version(vd, fd):
    if fd['prefver'] == vd['dccver']:
        return True
    else:
        return False

def get_handle(url):
    #  Takes url such as 'https://docushare.tmt.org:443/Version-501', returns 'Version-501'
    #  Replaces 'File' with 'Document'
    fileRegex = re.compile(r'File')
    handle = url.split('/')[-1]
    handle = fileRegex.sub('Document', handle)
    return(handle)

def file_read_collection(coll):
    htmlfile = '/Users/sroberts/Box Sync/Python/' + coll + '.html'
    fh=open(cf.dccfilepath + htmlfile,'r',encoding='utf-8').read()
    dom = BeautifulSoup(fh)
    clist = []
    for res in dom.find_all("response"):
        fd = {}
        fd['name'] = [res.displayname.text, get_handle(res.href.text)]
        fd['owner'] = [res.entityowner.displayname.text, res.entityowner.username.text,res.entityowner.dsref['handle']]
        fd['tmtnum'] = res.summary.text
        fd['parents'] = []
        for par in res.find_all("parents"):
            fd['parents'].append([par.dsref['handle'],par.displayname.text])
        clist.append(fd)
    return(clist)
    
def dcc_read_collection(s, coll_handle):
    dom = dom_prop_find(s, coll_handle)

    clist = []
    for res in dom.find_all("response"):
        fd = {}
        fd['name'] = [res.displayname.text, get_handle(res.href.text)]
        fd['owner'] = [res.entityowner.displayname.text, res.entityowner.username.text,res.entityowner.dsref['handle']]
        fd['tmtnum'] = res.summary.text
        fd['parents'] = []
        for par in res.find_all("parents"):
            fd['parents'].append([par.dsref['handle'],par.displayname.text])
        clist.append(fd)
    return(clist)
    
def dcc_get_coll_handles(s, c_handle):
    clist = dcc_read_collection(s, c_handle)
    h = []
    for c in clist:
        h.append(c['name'][1])
    return h    
        
def print_coll_info(clist):
    # pprint.pprint(clist)
    idx = 0
    for c in clist:
        if idx == 0:
            print("\nListing of: [", c['name'][1], "], \"", c['name'][0], "\"", sep = "")
            print("Owner: [", c['owner'][2], "], [", c['owner'][1], "], \"", c['owner'][0], "\"", sep = "")
            print("Parents:")
            for p in c['parents']:
                print("  [",p[0],"], \"", p[1], "\"", sep = "")
            print("\nContents:")
        else: 
            print("  ",'%2d' % idx, ": [", c['name'][1], "], \"", c['name'][0],"\"", sep="")
            print("  Owner: [", c['owner'][2], "], [", c['owner'][1], "], \"", c['owner'][0], "\"", sep = "")
            print("  TMTNum: [", c['tmtnum'], "]", sep = "")
            print("  Parents:")
            for p in c['parents']:
                print("    [",p[0],"], \"", p[1], "\"", sep = "")
            print("")
        idx += 1

def check_docs_in_coll(s, dl, cl):
    for c in cl:
        # get the list of documents in the collection
        cdl = get_files_in_collection(s, c)
        for d in dl:
            #  print('testing ', d, ' in ', cdl)
            if not d in cdl:
                print(d, ' not found in ', c)
            else:
                print(d, ' found in ', c)    
