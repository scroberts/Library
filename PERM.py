#!/usr/bin/env python3

# external modules
import sys

# my modules
import DCC
import Config as CF
import Tree
import MyUtil
import FileSys
import PERM_DEFS
import Match

debug = False

def get_group_handles(s,grp):
    fd = DCC.prop_get(s, grp, InfoSet = 'Group', Print = True, WriteProp = True)
    chandles = []
    for c in fd['children']:
        chandles.append(c[0])
    return(chandles)

def check_perms(s, set, handles, **kwargs):
    ask_flag = kwargs.get('Ask', True)
    if not ask_flag:
        if not MyUtil.get_yn('!!! Warning !!! ask = False: Will not ask to make changes, okay? Enter N to Exit, Y to Continue:'):
            print('exiting...')
            sys.exit(0)
    for handle in handles:
        if 'Document-' in handle:
            fd = DCC.prop_get(s, handle, InfoSet = 'DocBasic')
        elif 'Collection-' in handle:
            fd = DCC.prop_get(s, handle, InfoSet = 'CollData')
        else:
            fd = DCC.prop_get(s, handle, InfoSet = 'Title')    
        fd['permissions'] = DCC.prop_get(s, handle, InfoSet = 'Perms')
#         print(fd['handle'], ':', fd['title'])    
        
        print('\n>>>>>>>>>>>>>>       DCC Information       <<<<<<<<<<<<<<')
        if 'Document-' in handle:
            DCC.print_doc_basic(fd)
        elif 'Collection-' in handle:
            DCC.print_coll_data(fd)
        else:
            print('Not Document or Collection:', handle, ':', fd['title'])   
        print('\n\tDoc Properties URL: ',Tree.url_view(handle))
        print('\tPermissions URL: ',Tree.url_perm(handle))
        print('\tGet Document URL: ',Tree.url_access(handle))

        
        print()
    
        fix_objact(s, fd, handle, set, **kwargs)
        fix_permact(s, fd, handle, set, **kwargs)
        
def modify_dcc_perms(s, handle, permdata, **kwargs):
    ask_flag = kwargs.get('Ask',True)
    print('\n   Modifying Permissions to:',handle)
    DCC.print_perms(permdata)       
    if ask_flag == False or MyUtil.get_yn('Change Permissions (Y/N)?'):
        print('Changing permissions...')
        DCC.set_permissions(s, handle, permdata)

def make_perm_changes(s, handle, permdata, removelist, changelist, addlist, **kwargs):
    ask_flag = kwargs.get('Ask',True)
    mod_flag = False
    
    if ask_flag == True:
        ans = MyUtil.get_all_none_indiv('Make Changes? All/None/Individual (A/N/I)?')
        if ans == 'All':
            ask_flag = False
        elif ans == 'None':
            return
    
    for perm in removelist:
        print('Remove?: ',end='')
        DCC.print_perm(perm) 
        if ask_flag == False or MyUtil.get_yn(': (Y/N)?'):
            if ask_flag == False: print()
            mod_flag = True
            MyUtil.remove_dict_from_list(permdata['perms'],'handle',perm['handle'])

    for chperm in changelist:
        print('Change?:', end='')
        DCC.print_perm(chperm) 
        if ask_flag == False or MyUtil.get_yn(': (Y/N)?'):
            if ask_flag == False: print()
            mod_flag = True
            for perm in permdata['perms']:
                if perm['handle'] == chperm['handle']:
                    if 'Read' in perm: del(perm['Read'])
                    if 'Write'in perm: del(perm['Write'])
                    if 'Manage' in perm: del(perm['Manage'])
                    for key,val in chperm.items():
                        perm[key] = val
                              
    for addperm in addlist:
        print('Add?:', end='')
        DCC.print_perm(addperm)    
        if ask_flag == False or MyUtil.get_yn(': (Y/N)?'):
            if ask_flag == False: print()
            mod_flag = True
            permdata['perms'].append(addperm)
        if debug: DCC.print_perms(permdata)
    
    if mod_flag:
        # check ask_flag since it may have been modified from kwargs value
        if ask_flag == False:
            modify_dcc_perms(s, handle, permdata, Ask=False)
        else:
            modify_dcc_perms(s,handle,permdata, **kwargs)

def check_fd_sel(fd, set):
    try:
        obj_sel = set['ObjSel']['Criteria']
        if Match.parse(obj_sel, fd):
            return(True)
        return(False)
    except:
        if debug: print('ObjSel is not defined')
        return(True)

def check_perm_sel(permdata, set):
    # PermSel Criteria is a list of checks against permissions.  If the complete list passes
    # then the PermAct actions will be undertaken.
    try:
        perm_sels = set['PermSel']['Criteria']
        for perm_sel in perm_sels:
            if debug: print('check_perm_sel:',perm_sel)
            for perm in permdata['perms']:
                match_flag = False
                if Match.parse(perm_sel, perm):
                    match_flag = True
                    break
            if match_flag == False:
                if debug: print('check_perm_sel: returning False')
                return(False)
        if debug: print('check_perm_sel: returning True')
        return(True)
    except:
        if debug: print('PermSel is not defined')
        return(True)

def print_perm_changes(removelist, changelist, addlist):
    for perm in removelist:
        print('??? Remove ??? :',end='')
        DCC.print_perm(perm,LF=True)
    for perm in changelist:
        print('??? Change ??? :',end='')
        DCC.print_perm(perm,LF=True)
    for perm in addlist:
        print('??? Add ??? :',end='')
        DCC.print_perm(perm,LF=True)
    print()

def id_perm_changes(s, handle, fd, permdata, set):
    removelist = []
    changelist = []
    addlist = []
       
    if not check_fd_sel(fd, set) or not check_perm_sel(permdata, set):
        return([removelist,changelist,addlist])
    
    for perm_act in set['PermAct']:
        # pass if no action is defined
        if not perm_act['Action']:
            pass
        elif perm_act['Action']['Action'] == 'Remove':
            for perm in permdata['perms']:
                if Match.parse(perm_act['Criteria'], perm):
                    removelist.append(perm)
        elif perm_act['Action']['Action'] == 'Change':
            for perm in permdata['perms']:
                if Match.parse(perm_act['Criteria'], perm):
                    # delete the old permission
                    newperm = perm.copy()
                    if 'Read' in perm: del(newperm['Read'])
                    if 'Write'in perm: del(newperm['Write'])
                    if 'Manage' in perm: del(newperm['Manage'])
                    for key,val in perm_act['Action']['Perms'].items():
                        newperm[key] = val
                    changelist.append(newperm)  
        elif perm_act['Action']['Action'] == 'Add':
            addFlag = True
            for perm in permdata['perms']:
                if not Match.parse(perm_act['Criteria'], perm):
                    addFlag = False
            if addFlag:
                pEntry = {}
                pEntry['handle'] = perm_act['Action']['Handle']
                grpdata = DCC.prop_get(s, pEntry['handle'], InfoSet = 'Title')
                pEntry['name'] = grpdata['title']
                if 'Read' in perm_act['Action']['Perms']:
                    pEntry['Read'] = perm_act['Action']['Perms']['Read']
                if 'Write' in perm_act['Action']['Perms']:
                    pEntry['Write'] = perm_act['Action']['Perms']['Write']
                if 'Manage' in perm_act['Action']['Perms']:
                    pEntry['Manage'] = perm_act['Action']['Perms']['Manage']
                addlist.append(pEntry) 
                
        elif perm_act['Action']['Action'] == 'Message':
            for perm in permdata['perms']:
                if Match.parse(perm_act['Criteria'], perm):
                    print(perm_act['Action']['Message'])
                    DCC.print_perm(perm, LF = True)
        
    return([removelist, changelist, addlist])


def fix_objact(s, fd, handle, set, **kwargs):
    ask_flag = kwargs.get('Ask',True)
    
    if not check_fd_sel(fd, set):
        return
        
    for obj_act in set['ObjAct']:
        if not obj_act['Action']:
            pass

        if Match.parse(obj_act['Criteria'], fd):
            if obj_act['Action']['Action'] == 'SetOwner':
                nu = DCC.prop_get(s, obj_act['Action']['Owner'], InfoSet = 'User')
                print('??? Change Owner from [', fd['owner-userid'], ',', fd['owner-username'], '] to [', 
                                        nu['owner-userid'], ',', nu['owner-username'], ']', sep = '', end = '') 
                if ask_flag == False or MyUtil.get_yn(': (Y/N)? '):
                    DCC.change_owner(s, handle, obj_act['Action']['Owner'])
                    
            elif obj_act['Action']['Action'] == 'AddKeyword':
                print('??? Add Keyword "', obj_act['Action']['Keyword'], '" to "', fd['keywords'].strip(), '"', sep = '', end = '') 
                if ask_flag == False or MyUtil.get_yn(': (Y/N)? '):
                    kw = obj_act['Action']['Keyword'] + fd['keywords'].strip(' ')
                    DCC.set_metadata(s, handle, Keywords = kw)

            elif obj_act['Action']['Action'] == 'DelKeyword':
                print('??? Remove Keyword "', obj_act['Action']['Keyword'], '" from "', fd['keywords'], '"', sep = '', end = '') 
                if ask_flag == False or MyUtil.get_yn(': (Y/N)? '):
                    kw = fd['keywords'].strip(' ').replace(obj_act['Action']['Keyword'], '')
                    DCC.set_metadata(s, handle, Keywords = kw)
                
            elif obj_act['Action']['Action'] == 'RepTitle':
                print('??? Change Title to "', obj_act['Action']['Title'], '" from "', fd['title'], '"', sep = '', end = '') 
                if ask_flag == False or MyUtil.get_yn(': (Y/N)? '):
                    DCC.set_metadata(s, handle, Title = obj_act['Action']['Title'])

            elif obj_act['Action']['Action'] == 'RepTmtNum':
                print('??? Change TmtNum to "', obj_act['Action']['TmtNum'], '" from "', fd['tmtnum'], '"', sep = '', end = '') 
                if ask_flag == False or MyUtil.get_yn(': (Y/N)? '):
                    DCC.set_metadata(s, handle, Summary = obj_act['Action']['TmtNum'])
                pass
                
            elif obj_act['Action']['Action'] == 'Message':
                print(obj_act['Action']['Message'])
                
            else:
                print('Error in PERM.fix_objact: ObjAct Action not recognized:', obj_act['Action']['Action'])
            

def fix_permact(s, fd, handle, set, **kwargs):
    # kwargs
    #   ask = True | False, Do/Don't ask if changes should be made (!!! Dangerous !!!)
    #   default is ask

    [removelist, changelist, addlist] = id_perm_changes(s,handle, fd, fd['permissions'], set) 
    ch_flag = False
    if len(removelist) or len(changelist) or len(addlist):

        DCC.print_perms(fd['permissions'])    
        print('\nSuggested Changes...')
        print_perm_changes(removelist, changelist, addlist)
        make_perm_changes(s, handle, fd['permissions'], removelist, changelist, addlist, **kwargs)

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
            for perm in sorted(fd["permissions"]["perms"], key = lambda x: x["handle"]):
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
            

def test_fix_permact():
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)
    
    set = PERM_DEFS.setA
    handle = 'Document-27819'
        
    fix_permact(s, handle, set)


def test_id_perm_changes():
    fd = FileSys.file_read_json('Document-4780_DocBasic')
    permdata = FileSys.file_read_json('Document-4780_Perms')
    handle = 'Document-4780'
    set = PERM_DEFS.setA
    
    [removelist, changelist, addlist] = id_perm_changes(handle, fd, permdata, set) 
    print('Remove:', removelist)
    print('Change:', changelist)
    print('Add:', addlist)    
    make_perm_changes(s, handle, permdata, removelist, changelist, addlist)

if __name__ == '__main__':
    print("Running module test code for",__file__)
#     testPerm()
#     testFixPerm()
#     test_id_perm_changes()
    test_fix_permact()

    
    
    