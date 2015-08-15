#!/usr/bin/env python3

# external modules

# my modules
import DCC
import config as cf

def printCheckPerms(perm):
    read_okay = False
    print("[",perm["handle"],"]:\t","perms = ",sep="",end="")
    if "Search" in perm.keys():
        print("[Search]", end="")
    if "Read" in perm.keys():
        print("[Read]", end="")
        read_okay = True
    if "Write" in perm.keys():
       print("[Write]", end="")
    if "Manage" in perm.keys():
        print("[Manage]", end="")
    print(", \"",perm['name'],"\"",sep="")
    return read_okay

def checkPerms(target, permissions):
    # Login to DCC
    s = DCC.login(cf.dcc_url + cf.dcc_login)

    doclist = DCC.get_files_in_collection(s, target)

    for doc in doclist:
        dom = DCC.dom_prop_find(s, doc)
        fd = DCC.read_dcc_doc_data(dom)
    
        print("\n\n*** Document Entry", fd['dccnum'], "***\n")
        print("DCC Document Number/Name: ", fd['dccnum'],", \"",fd['dccname'],"\"",sep="")
        print("TMT Document Number: ", fd['tmtnum'])
        print("https://docushare.tmt.org/docushare/dsweb/ServicesLib/" + fd['dccnum'] + "/view")
    
        OkayPerms = []
        for perm in sorted(fd["permissions"], key = lambda x: x["handle"]):
            # Go through each set and create a dictionary of entries that have perms okay
            for sets in permissions:
                for item in sets:
                    if perm["handle"] == item:
                        if printCheckPerms(perm) == True:
                            OkayPerms.append(item)
        permFlag = False
        for sets in permissions:
            testFlag = True
            for item in sets:
                if not item in OkayPerms:
                    testFlag = False
            if testFlag == True:
                permFlag = True
                        
        if permFlag == True:
            print("Access to this document meets criteria")
        else:
            print("!!! PERMISSIONS PROBLEM - Access Criteria Fail !!!")