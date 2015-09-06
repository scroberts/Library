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
import config as cf
import tree

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
            url = cf.dcc_url + "/dsweb/COPY/" + d
            headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "DESTINATION": c}
            r = s.post(url, headers=headers)
            print(r.text)
            
def change_owner(s, dochandle, userhandle):
    url = cf.dcc_url + "/dsweb/PROPPATCH/" + dochandle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop><entityowner><dsref handle="'''
    xml += userhandle
    xml += '''"/></entityowner></prop></set></propertyupdate>'''
    print(xml)
    r = s.post(url,data=xml,headers=headers)
    print(r.text)
    print(r.headers)
    print("Owner Change Status Code:", r.status_code)
    
def check_docs_in_coll(s, dl, cl):
    for c in cl:
        # get the list of documents in the collection
        
        cdl = list_obj_in_coll(s,c,Print=True,Jwrite=False,Depth='infinity',Type='Doc',WriteProp=False)

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
    url = cf.dcc_url + "/dsweb/MOVE/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml", "SOURCE": source, "DESTINATION": dest}
    r = s.post(url, headers=headers) 
    print(r.text)
    
def dcc_remove_doc_from_coll(s, handle, coll):
    """ Removes the location of the document from the collection
        handle - the document handle
        coll - the parent collection
    """
    # First find other collections where the document exists
    loc = prop_get(s, handle, InfoSet = 'Parents', WriteProp = True)
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
    url = cf.dcc_url + "/dsweb/GET/" + handle
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
    webfile = open(cf.dccfilepath + outfile,'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close
    
def file_read_collection(coll):
    # Reads collection data from a .html file on disk
    htmlfile = '/Users/sroberts/Box Sync/Python/' + coll + '.html'
    fh=open(cf.dccfilepath + htmlfile,'r',encoding='utf-8').read()
    dom = BeautifulSoup(fh)
    clist = read_coll_content(dom)
    return(clist)
    
def file_write_props(r, fname):
    webfile = open(cf.dccfilepath + fname +".html",'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close
    
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

    fd = prop_get(s, collhandle, InfoSet = 'Coll', Depth = depth, WriteProp = writeprop)
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
        fh = open(cf.dccfilepath + collhandle + file_ext,'w')
        json.dump(objlist, fh)
        fh.close()
    return(objlist)
    
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
        print('Login status code:', r.status_code)
    except:
        print("Unable to log in")
        print("Status Code:", r.status_code)
        exit(0)
        
    c = s.cookies
    # print('Cookies:\n', c)
    return s
    
def mkCol(s,parentColl, collName, collDesc):
    # Create a collection, return the handle
    url = cf.dcc_url + "/dsweb/MKCOL/" + parentColl
    
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
     
    xml1 = """<?xml version="1.0" ?><propertyupdate><set><prop><displayname><![CDATA["""
    xml2 = """]]></displayname><description>"""
    xml3 = """</description></prop></set></propertyupdate>"""
    xml = xml1 + collName + xml2 + collDesc + xml3   
    
    r = s.post(url,data=xml,headers=headers)  # Gets limited data
    
    handle = r.headers['docushare-handle']
    return(handle)  
    
def prop_get(s, handle, **kwargs):
    # kwargs options:
    #  Depth - Level to get Collection children information ('0', '1' or 'infinity')
    #       '0' returns information on Collection itself
    #       '1' and 'infinity' return information on Collection content
    #  InfoSet = Children - Collection Children
    #  InfoSet = Coll - Collection information (See Depth)
    #  InfoSet = DocAll - All Document information
    #  InfoSet = DocBasic - Document basic information
    #  InfoSet = DocDate - Document last modified date
    #  InfoSet = Parents - Locations of documents or collections
    #  InfoSet = Perms - Document Permissions
    #  InfoSet = VerAll - All Version information
    #  RetDom - Return BeautifulSoup object rather than file data structure
    #  WriteProp = (True|False)
    
    url = cf.dcc_url + "/dsweb/PROPFIND/" + handle
    headers = {"DocuShare-Version":"5.0", "Content-Type":"text/xml", "Accept":"text/xml"}
    infoDic = { 'DocBasic':'<title/><handle/><document/><getlastmodified/><size/><summary/>',
                'DocDate': '<getlastmodified/>',
                'Parents': '<parents/>',
                'Children' : '<children/>',
                'Perms': '<private/><acl/>',
                'Coll' : '<children/><title/><displayname/><summary/><entityowner/><getcontenttype/><parents/><getlastmodified/>',
                'Summary' : '<summary/>'}

    infoSet = kwargs.get('InfoSet','DocBasic')
    writeRes = kwargs.get('WriteProp', True)
    retDom = kwargs.get('RetDom',False)
    depth = kwargs.get('Depth','0') 
    headers['Depth'] = depth
    
    if infoSet in infoDic:
        xml = """<?xml version="1.0" ?><propfind><prop>""" + infoDic[infoSet] + """</prop></propfind>"""
        r = s.post(url,data=xml,headers=headers)
    else:
        r = s.post(url,headers=headers)

    if writeRes:
        file_write_props(r, handle + '_' + infoSet)
    dom = BeautifulSoup(r.text)
    if retDom:
        return(dom)
    fd = prop_scrape(dom, infoSet, depth)
    return(fd)
    
def prop_scrape(dom, infSet, depth):
    if infSet == 'DocBasic':
        fd = {}
        fd['title'] = dom.title.text
        fd['filename'] = dom.document.text
        fd['handle'] = dom.dsref['handle']
        fd['author'] = dom.author
        fd['date'] = dom.getlastmodified.text
        fd['size'] = int(dom.size.text)
        fd['tmtnum'] = dom.summary.text
    elif infSet == 'DocDate':
        date = dom.getlastmodified.text
        fd = {'date':date}
    elif infSet == 'Parents':
        fd = []
        for par in dom.find("parents").find_all("dsref"):
            fd.append([par['handle'],par.displayname.text])
    elif infSet == 'Children':
        fd = []
        for par in dom.find("children").find_all("dsref"):
            fd.append([get_handle(par['handle']),par.displayname.text])
    elif infSet == 'DocAll':
        fd = read_doc_data(dom)
    elif infSet == 'VerAll':
        fd = read_ver_data(dom)        
    elif infSet == 'Coll':
        if depth == '0':
            fd = read_coll_data(dom)
        else:
            fd = read_coll_content(dom)
    elif infSet == 'Perms':
        fd = read_doc_perms(dom)
    return(fd) 
    
def print_coll_children(fd):
    print("Children...")
    for c in fd['children']:
        print("  [",c[0],"], \"", c[1], "\"", sep = "")

def print_coll_data(fd):
    # used for Depth = '0'
    print("\n\n*** Collection Handle", fd['handle'], "***\n")
    print("Title: ", fd['title'])
    print("Summary: ", fd['summary'])
    print("Modified Date: ", fd['modified'])
    print("Owner: ", fd['owner-name'],":[",fd['owner-userid'],",",fd['owner-username'],"]", sep="")
      
def print_coll_info(clist):
# Used for depth of '1' or 'infinity'
    # pprint.pprint(clist)
    idx = 0
    for c in clist:
        if idx == 0:
            print("\nListing of: ",sep = "",end="")
            print_coll_info_entry('',c)
            print("\nContents:")
        else: 
            print("  ",'%2d' % idx, ": ", sep="", end="")
            print_coll_info_entry('    ',c)
            print("")
        idx += 1
       
def print_coll_info_entry(indent,c):
    print(" [", c['name'][1], "], \"", c['name'][0], "\"", sep = "")
    print(indent,"Summary: ", c['summary'], sep = "")
    print(indent,"Last Modified: ", c['modified'], sep = "")
    print(indent,"Owner: [", c['owner'][2], "], [", c['owner'][1], "], \"", c['owner'][0], "\"", sep = "")
    print(indent,"Parents:", sep = "")
    for p in c['parents']:
        print(indent,"  [",p[0],"], \"", p[1], "\"", sep = "")
    
def print_coll_parents(fd):   
    print("Parents...")
    for p in fd['parents']:
        print("  [",p[0],"], \"", p[1], "\"", sep = "")

def print_doc_basic_info(fd):    
    print("DCC Title: ", fd['title'])
    print("DCC Document Handle/FileName: ", fd['handle'],", \"",fd['filename'],"\"",sep="")
    print("DCC Date: ", fd['date'])
    print("Size: ", fd['size'])
    
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
    print_perm_info(fd['permissions'])
    print("\nLocations...")
    for loc in sorted(fd['locations'], key = lambda x: x[0]):
        print(loc[0],", \"",loc[1],"\"", sep="")
    print("\nVersions...")
    for ver in sorted(fd["versions"], key = lambda x: x[2], reverse = True ):
        print("Version:", ver[2], ", [", ver[0], "], [",ver[3], "], \"", ver[1], "\"", sep="")
    print("\n*** End Document Entry", fd['dccnum'], "***\n")
    
def print_perm_info(permlist):
    print("Permissions...")
    for perm in sorted(permlist, key = lambda x: x["handle"]):
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

def read_coll_content(dom):
# Used for depth of '1' or 'infinity'
    clist = []
    for res in dom.find_all("response"):
        fd = {}
        fd['name'] = [res.displayname.text, get_handle(res.href.text)]
        fd['title'] = res.displayname.text
        fd['handle'] = get_handle(res.href.text)
        fd['owner-name'] = dom.entityowner.displayname.text
        fd['owner-username'] = dom.entityowner.username.text
        fd['owner-userid'] = dom.entityowner.dsref['handle']
        fd['owner'] = [fd['owner-name'], fd['owner-username'], fd['owner-userid']]
        fd['summary'] = res.summary.text
        fd['modified'] = dom.getlastmodified.text
                   
        clist.append(fd)
    return(clist)
       
def read_coll_data(dom):
    # Applies to collection data for Depth = '0'
    fd = {}
    fd['title'] = dom.title.text
    fd['dccnum'] = get_handle(dom.response.href.text)
    fd['handle'] = get_handle(dom.response.href.text)
    fd['summary'] = dom.summary.text
    fd['modified'] = dom.getlastmodified.text
    fd['date'] = dom.getlastmodified.text
    fd['owner-name'] = dom.entityowner.displayname.text
    fd['owner-username'] = dom.entityowner.username.text
    fd['owner-userid'] = dom.entityowner.dsref['handle']
    return(fd)
    
def read_doc_data(dom):
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
    fd["permissions"] = read_doc_perms(dom)
    return(fd)
    
def read_doc_perms(dom):
    fd = {}
    # Permissions
    perms = []
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
            perms.append(pentry)  
        except:
            pass
    return(perms)
    
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
    
def set_permissions(s,handle,fd):
    # fd follows the permissions dictionary format
    
    url = cf.dcc_url + "/dsweb/PROPPATCH/" + handle
    headers = {"DocuShare-Version":"6.2", "Content-Type":"text/xml", "Accept":"*/*, text/xml", "User-Agent":"DsAxess/4.0", "Accept-Language":"en"}
    xml = '''<?xml version="1.0" ?><propertyupdate><set><prop><acl handle="''' 
    xml += handle
    xml += '''">'''
    for entry in fd:
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
    xml += '''</acl></prop></set></propertyupdate>'''
    r = s.post(url,data=xml,headers=headers)
    print("Permission Change Status Code:", r.status_code)

             
if __name__ == '__main__':
    print("Running module test code for",__file__)

#     testGetProps()
#     testGetBasicInfo()
#     testTraverse()
    testGetColl()