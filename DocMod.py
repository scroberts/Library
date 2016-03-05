#!/usr/bin/env python3

# References: 
# http://omz-software.com/pythonista/docs/ios/requests.html
# http://stackoverflow.com/questions/595872/under-what-conditions-is-a-jsessionid-created

# External Modules
import re
import os
import json
import getpass
# import platform
from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from requests.auth import HTTPDigestAuth
from requests.auth import HTTPBasicAuth


# My modules
import DCC
import Config as CF


def tracetree_login():
    # See if secrets file exists and if so use credentials from there
    try:
        import secrets
        uname = secrets.pw['TT']['login']
        pword = secrets.pw['TT']['password']
    except:
        uname = input("Enter TMT TraceTree Username:")
        pword = getpass.getpass()

    try:
        s = requests.session()
        s.auth = (uname,pword)
    except:
        print("Unable to log in")
        exit(1)
        
    return(s)

def get_docmod_html_files(s, **kwargs):

    verify_flag = True
#     if platform.system() == 'Windows':
#         verify_flag = False

    use_cache = kwargs.get('InfoSet',False)

    try:
        res = s.get(CF.docs_url_main, verify = verify_flag)
        res.raise_for_status()
    except:
        print('Unable to get from TraceTree, check login credentials')
#         print('Status code:', res.status_code)
        exit(1)

    webfile = open(CF.tracetreefilepath + 'document_module_main.html','wb')
    for chunk in res.iter_content(100000):
        webfile.write(chunk)
    webfile.close

    dom = BeautifulSoup(res.text, "html.parser")
    urls = []

    for link in dom.find_all('a'):
        url = link.get('href')
        if url:
            urls.append(url)
    # Every 2nd url is a duplicate
    urls = urls[1::2]

    # Check for urls in format all numbers + html

    goodurl = re.compile(r'\d.html')
    
    newurllist = []
    for url in urls:
        if goodurl.search(url):
            newurllist.append(url)
            if use_cache and os.path.isfile(CF.tracetreefilepath + url):
                print('Found existing file: ', url)
            else:
                print('Reading and saving: ', url)
                res = s.get(CF.docs_url_base + url)
                res.raise_for_status()
                webfile = open(CF.tracetreefilepath + url,'wb')
                for chunk in res.iter_content(100000):
                    webfile.write(chunk)
                webfile.close
    return(newurllist)
            
def get_tracetree_docmod_dict(url):
    file = open(CF.tracetreefilepath + url,'r',encoding='latin-1').read()
    dom = BeautifulSoup(file, "html.parser")
    dict = {}
    for child in dom.table.children:  
        try:
            field = child.td.string.strip()  
#             print(field)
            try:
                next = child.td.next_sibling.next_sibling
                value = next.string.strip() 
#                 print('value', value)
            except:
#                 print('child.tr.td',child.tr.td)
                value = child.tr.td.string.strip()
#                 print('value',value)
                    
            dict[field] = value
#             print("[",field,"]","[", value, "]")
        except: 
    #         print("rejected", type(child))
            pass    
    return(dict)

def build_docmod_dict(urls):
    docmod = {}
    for url in urls:
        objname = url[0:url.find('.')]
        print('Building document module for DOORS Object ', objname)
        docmod[objname] = get_tracetree_docmod_dict(url)
    return docmod


def create_docmod_file(filename):
    s = tracetree_login()
    urls = get_docmod_html_files(s)

    fh = open(CF.tracetreefilepath + CF.docmod_url_list_file,'w')
    json.dump(urls, fh)
    fh.close()

    docmod = build_docmod_dict(urls)
    
    fh = open(CF.tracetreefilepath + CF.docmod_dict_file,'w')
    json.dump(docmod, fh)
    fh.close()

# Checks if the dict entries in criteria are in target  
def is_in_dict(criteria, target):
    match = True
    for name, value in criteria.items():
        try:
            if value == '_UNASSIGNED':
                if name in target:
                    match = False
            elif target[name] != value:
                match = False
        except:
            match = False
    return(match)
    
def test_is_in_dict():
    scott = {}
    scott['first'] = 'Scott'
    scott['last'] = 'Roberts'
    scott['age'] = 52
    scott['city'] = 'Victoria'
    scott['country'] = 'Canada'

    test = {}
    test['city'] = 'Victoria'
    test['last'] = 'Roberts'
    test['country'] = 'Canada'

    match = is_in_dict(test,scott)
    print('match = ', match)
    
def print_report(docmodreport, doc):
    for name in docmodreport:
#         print('print_report name: ', name)
#         print('print_report doc: ', doc)
        try:
            print('\t', name, ' = ', doc[name], sep = '')
        except:
            print('\t', name, ' = ', 'No Attribute Value Assigned', sep = '')
            
            
if __name__ == '__main__':
    dict = get_tracetree_docmod_dict('1796.html')
    print(dict)
    



        
