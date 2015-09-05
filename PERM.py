#!/usr/bin/env python3

# external modules

# my modules
import DCC
import config as cf
import tree
import sys

def printCheckCriteria(target, permissions):
    setnum = 0
    print('\n+++ Criteria for permissions check: +++')
    print('All permissions within a set must be met for the set to pass')
    print('Permissions pass if any set passes test')
    print('Looking at files in {0} and below', target)
    for set in permissions:
        setnum += 1
        print('\tSet #', setnum) 
        for item,plist in set.items():
            print('\t\t',item, end = '')
            print('\t[ ', end='')
            if 'R' in plist:
                print('Read ', end = '')
            if 'W' in plist:
                print('Write ', end = '')
            if 'M' in plist:
                print('Manage ', end = '')
            print(']')

def printCheckPerms(perm,plist):
    read_okay = False
    write_okay = False
    manage_okay = False
    perms_okay = True
    print("[",perm["handle"],"]:\t","perms = ",sep="",end="")
    if "Search" in perm.keys():
        print("[Search]", end="")
    if "Read" in perm.keys():
        print("[Read]", end="")
        read_okay = True
    if "Write" in perm.keys():
        print("[Write]", end="")
        write_okay = True
    if "Manage" in perm.keys():
        print("[Manage]", end="")
        manage_okay = True
    print(", \"",perm['name'],"\"",sep="")
    
    if 'R' in plist and read_okay == False:
        perms_okay = False
    if 'W' in plist and write_okay == False:
        perms_okay = False
    if 'M' in plist and manage_okay == False:
        perms_okay = False
    
    return perms_okay

def checkPerms(target, permissions):
    # Login to DCC
    s = DCC.login(cf.dcc_url + cf.dcc_login)

    if 'Collection' in target:
#         docList = [target]
#         docList = docList + DCC.get_files_in_collection(s, target)
#         docList = docList + DCC.get_collections_in_collection(s, target)
#         print(docList)
        tr = tree.get_tree(s,target)
        tree.print_tree(tr)
        docList = tree.get_flat_tree(tr)
        
    else:
        docList = [target]
    
    printCheckCriteria(target, permissions)
    passList = []
    failList = []

    for doc in docList:
        checkFlag = True
        if 'Document' in doc:
#             dom = DCC.dom_prop_find(s, doc)
#             fd = DCC.read_dcc_doc_data(dom)
            fd = DCC.getProps(s, doc, InfoSet = 'DocBasic', WriteProp = True)
            fd['permissions'] = DCC.getProps(s, doc, InfoSet = 'Perms', Depth = '0', WriteProp = True)
    
            print("\n\n*** Document Entry", fd['handle'], "***")
            print("DCC Name: \"",fd['title'],"\"",sep="")
            print("TMT Document Number: ", fd['tmtnum'])
            print("https://docushare.tmt.org/docushare/dsweb/ServicesLib/" + fd['handle'] + "/view")
        elif 'Collection' in doc:
            fd = DCC.getProps(s, doc, InfoSet = 'Coll', Depth = '0', WriteProp = True)
            fd['permissions'] = DCC.getProps(s, doc, InfoSet = 'Perms', Depth = '0', WriteProp = True)
#             dom = DCC.dom_prop_find_coll(s, doc)
#             fd = DCC.read_dcc_coll_data(dom)
            print("\n\n*** Collection Entry", fd['dccnum'], "***")
            print("https://docushare.tmt.org/docushare/dsweb/ServicesLib/" + fd['dccnum'] + "/view")
        else:
            checkFlag = False
            print("\nNot checking permissions on object that is not a Collection or Document):",doc) 

        if checkFlag:
            OkayPerms = []
            for perm in sorted(fd["permissions"], key = lambda x: x["handle"]):
                # Go through each set and create a dictionary of entries that have perms okay
                for sets in permissions:
                    for item,plist in sets.items():
                        if perm["handle"] == item:
                            if printCheckPerms(perm,plist) == True:
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
                print("*** PERMISSIONS MEET CRITERIA ***")
                passList.append(doc)
            else:
                print("!!! PERMISSIONS DO NOT MEET CRITERIA !!!")
            failList.append(doc)
            
    return([passList,failList])
            
def testPerm():
    # Define a list data structure of users or groups in sets that are
    # acceptable if they have read permission to the collections and files
    # The with the following logic: 
    #
    #   All contents of sets must be acceptable in an AND case (i.e. every
    #       member of a set must have read access to be acceptable) 
    #
    #   Permissions will be acceptable if any set is acceptable in an OR
    #     	sense (i.e. if one set meets the criteria then the the
    #     	permissions are considered okay)

    # Define the top level collection or document to check
    target = 'Collection-10071'
#     target = 'Document-21380'
#     target = 'Collection-1318'
    
    # Define users or groups that will be checked for permissions
    sys_eng_read = 'Group-325'
    se_group = 'Group-103'
    content_admin = 'Group-2'
    sr_user = 'User-50'
    tc_user = 'User-1165'
    
    # Define the permissions
    permissions = [{tc_user : 'RWM'}]
#     permissions = [{sys_eng_read : 'R'},{se_group : 'RW', content_admin : 'RWM'}, {sr_user : 'RWM'}]

    # Call the checkPerms function
    [passList,failList] = checkPerms(target, permissions)
    
    print('\n\n')
    print('List of docs that pass:', passList)
    print('List of docs that fail:', failList)
            
if __name__ == '__main__':
    print("Running module test code for",__file__)
    testPerm()

    
    
    