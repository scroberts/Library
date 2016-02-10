#!/usr/bin/env python3

from bs4 import BeautifulSoup
import re
import json

# The html file is saved from a Word Document containing links to Docushare.  
# This program extracts the Document and Version links from the file.

def get_url_word(outnameroot, htmlfile):

    # This is a new encoding.  I found what it was from the footer of TextWrangler.  
    # Here is a reference to encoding types used by Python
    # https://docs.python.org/2.4/lib/standard-encodings.html

    fh=open(htmlfile,'r',encoding='mac_roman').read()
    dom = BeautifulSoup(fh, "html.parser")

    doclist = []
    verlist = []
    bothlist = []

    docregex = re.compile(r'Document-\d+')
    verregex = re.compile(r'Version-\d+')
    for link in dom.find_all('a'):
        str = link.get('href')
        if str != None:
            print(str)
        
            mo1 = docregex.search(str)
            if mo1 != None:
                docstr = mo1.group()
                print(docstr)
                doclist.append(docstr)
                bothlist.append(docstr)
        
            mo1 = verregex.search(str)
            if mo1 != None:
                verstr = mo1.group()
                print(verstr)
                verlist.append(verstr)
                bothlist.append(verstr)
            
#     print(doclist)
#     print(verlist)
#     print(bothlist)

    fh = open(outnameroot + 'doclist.txt','w')
    json.dump(doclist,fh)
    fh.close()

    fh = open(outnameroot + 'verlist.txt','w')
    json.dump(verlist,fh)
    fh.close()

    fh = open(outnameroot + 'bothlist.txt','w')
    json.dump(bothlist,fh)
    fh.close()
    
def test_get_url_word():
    htmlfile = 'NFIRAOS_CID.htm'
    outroot = 'NFIRAOS_'
    get_url_word(outroot, htmlfile)   
    
# test_get_url_word()
