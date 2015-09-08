#!/usr/bin/env python3

# external modules
import sys

# my modules
import DCC
import Config as CF
import Tree
import MyUtil

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

def check_criteria(perm, action):
    PermReadFlag = perm.get('Read',False)
    PermWriteFlag = perm.get('Write',False)
    PermManageFlag = perm.get('Manage',False)
    PermSearchFlag = perm.get('Search',False)
    
    cFlag = True
    for crit,val in action['Criteria'].items():
#         print('Criteria: ', crit, val)
        if crit == 'HandleContains' and not val in perm['handle']:
#             print('Fail on HandleContains')
            cFlag = False
        if crit == 'Absent' and val in perm['handle']:
            cFlag = False
        if crit == 'Search' and not val == PermSearchFlag:
#             print('Fail on ReadFlag')
            cFlag = False 
        if crit == 'Read' and not val == PermReadFlag:
#             print('Fail on ReadFlag')
            cFlag = False 
        if crit == 'Write' and not val == PermWriteFlag:
#             print('Fail on WriteFlag')
            cFlag = False 
        if crit == 'Manage' and not val == PermManageFlag:
#             print('Fail on ManageFlag')
            cFlag = False                               
    return(cFlag)

def modify_dcc_perms(s,handle,perms):
    print('Modifying Permissions to:',handle)
    DCC.print_perms(perms)       
    if MyUtil.get_yn('Change Permissions (Y/N)?'):
        print('Changing permissions...')
        DCC.set_permissions(s, handle, perms)

def fixPerm(s, handle, actions):
    if 'Document-' in handle:
        fd = DCC.prop_get(s, handle, InfoSet = 'DocBasic', Print = True)
    elif 'Collection-' in handle:
        fd = DCC.prop_get(s, handle, InfoSet = 'CollData', Print = True)
    else:
        print('Not Document or Collection, not touching')
        
    perms = DCC.prop_get(s, handle, InfoSet = 'Perms', Print = True)
    print('#################### ENTRY ####################')
    
    removelist = []
    addlist = []
       
    for action in actions:
            if action['Action'] == 'Remove':
                exclude = action.get('Exclude',[])
                for perm in perms:
                    if (not perm['handle'] in exclude) and check_criteria(perm, action):
                        print('Modify (Remove): ',action['Action'],':',perm['handle'],':',perm['name'],sep='')
                        removelist.append(perm)
            if action['Action'] == 'Add':
                addFlag = True
                for perm in perms:
                    if not check_criteria(perm, action):
                        addFlag = False
                if addFlag:
                    pEntry = {}
                    print('Modify (Add): ',action['Action'],action['Handle'],action['Perms'])
                    pEntry['handle'] = action['Handle']
                    grpdata = DCC.prop_get(s, pEntry['handle'], InfoSet = 'Title')
                    pEntry['name'] = grpdata['title']
                    if 'Read' in action['Perms']:
                        pEntry['Read'] = action['Perms']['Read']
                    if 'Write' in action['Perms']:
                        pEntry['Write'] = action['Perms']['Write']
                    if 'Manage' in action['Perms']:
                        pEntry['Manage'] = action['Perms']['Manage']
                    addlist.append(pEntry)  
    print('')     
    changeFlag = False
    
    for perm in removelist:
        print('Remove?: ',perm['handle'],':',perm['name'],end='')
        if MyUtil.get_yn('(Y/N)?'):
            changeFlag = True
            MyUtil.remove_dict_from_list(perms,'handle',perm['handle'])
    for perm in addlist:
        print('Add?:', perm, end='')
        if MyUtil.get_yn('(Y/N)?'):
            changeFlag = True
            perms.append(perm)
    
    if changeFlag:
        modify_dcc_perms(s,handle,perms)

def checkPerms(target, permissions):
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)

    if 'Collection' in target:
        tr = Tree.get_tree(s,target)
        Tree.print_tree(s, tr)
        docList = Tree.get_flat_tree(tr)
        
    else:
        docList = [target]
    
    printCheckCriteria(target, permissions)
    passList = []
    failList = []

    for doc in docList:
        checkFlag = True
        if 'Document' in doc:
            fd = DCC.prop_get(s, doc, InfoSet = 'DocBasic')
            fd['permissions'] = DCC.prop_get(s, doc, InfoSet = 'Perms', Depth = '0')
    
            print("\n\n*** Document Entry", fd['handle'], "***")
            print("DCC Name: \"",fd['title'],"\"",sep="")
            print("TMT Document Number: ", fd['tmtnum'])
            print("https://docushare.tmt.org/docushare/dsweb/ServicesLib/" + fd['handle'] + "/view")
        elif 'Collection' in doc:
            fd = DCC.prop_get(s, doc, InfoSet = 'CollData')
            fd['permissions'] = DCC.prop_get(s, doc, InfoSet = 'Perms', Depth = '0')
            print("\n\n*** Collection Entry", fd['handle'], "***")
            print("https://docushare.tmt.org/docushare/dsweb/ServicesLib/" + fd['handle'] + "/view")
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
            
def testFixPerm():
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)
     
    collhandle = 'Collection-286'
    exclude = ['Collection-7337','Document-21244', 'Document-26018']

    print('excluding from Tree:',exclude)
    tree = Tree.get_tree(s, collhandle, Exclude = exclude)
    Tree.print_tree(s,tree)
    
    print('\n\n')
    for branch in tree:
        print(branch+': ',tree[branch])
    
#     collhandle = 'Collection-10892'
#     dochandle = 'Document-27819'
#     dochandle = 'Document-2688'
#     collhandle = 'Collection-10892'
    
    actions = [ {'Criteria' : {'HandleContains' : 'User-', 'Read' : True, 'Write' : False, 'Manage' : False}, 'Action' : 'Remove'},
                {'Criteria' : {'HandleContains' : 'Group-', 'Read' : True, 'Write' : False, 'Manage' : False}, 'Exclude' : ['Group-325'], 'Action' : 'Remove'},
                {'Criteria' : {'Read' : False, 'Write' : False, 'Manage' : False}, 'Action' : 'Remove'},
                {'Criteria' : {'HandleContains' : 'Group-4'}, 'Action' : 'Remove'},
                {'Criteria' : {'Absent' : 'Group-325'}, 'Action' : 'Add', 'Handle': 'Group-325', 'Perms' : {'Read':True}},
                {'Criteria' : {'Absent' : 'Group-103'}, 'Action' : 'Add', 'Handle': 'Group-103', 'Perms' : {'Read':True, 'Write':True}}]

    flatTree = Tree.flat_tree(tree, 'root', [])
    
    for handle in flatTree:
        fixPerm(s,handle, actions)

if __name__ == '__main__':
    print("Running module test code for",__file__)
#     testPerm()
    testFixPerm()

    
    
    