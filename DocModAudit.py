#!/usr/bin/env python3

# external modules
import DocMod
import os
import json

# my modules
import DCC
import Config as CF
import PERM_DEFS as PD
import PERM
import Tree
import MyUtil

# This code takes a search criteria, defined in "docinfo", and searches
# the DOORS document module (as stored in TraceTree) to find matches. 
# It prints a report on all files found based on the list of attributes
# in "docmodreport".
# In setting search criteria it is possible to look for undefined
# attributes by using '_UNASSIGNED' as the matching criteria.

            
found_flag = False
if os.path.isfile(CF.tracetreefilepath + CF.docmod_dict_file):
    print('Found existing DocMod file: ', CF.docmod_dict_file)
    found_flag = True
    
if found_flag == False or MyUtil.get_yn('Create New DocMod File (Y/N)? : '):
    print('Creating DocMod file: ', CF.docmod_dict_file)
    DocMod.create_docmod_file(CF.docmod_dict_file)
    
# Open the document module
fh = open(CF.tracetreefilepath + CF.docmod_dict_file,'r')
dm = json.load(fh)
fh.close()

# construct reflist to determine the search criteria
reflist = {}

docinfo = {}
docinfo['TMTPublished'] = 'True'
reflist['ICD'] = docinfo

# construct document module report list
docmodreport = []
docmodreport.append('dccDocTitle')
docmodreport.append('dccDocNo')
docmodreport.append('dccDocRev')
docmodreport.append('DocType')
docmodreport.append('dccDocHandleHyperlink')
docmodreport.append('dccDocVersionHyperlink')
docmodreport.append('dccDocSignedApproved')
docmodreport.append('TMTPublished')
docmodreport.append('dccStatusCheckDate')
docmodreport.append('dccDocHandleNo')

s = DCC.login(CF.dcc_url + CF.dcc_login)

docmodlist = []

pub_coll = 'Collection-8277'

tr = Tree.return_tree(s, pub_coll, 'Tree_' + pub_coll)
pub_list = Tree.get_flat_tree(tr)

docmatch = {}

for ref in reflist.items():
    print('looking for ', ref[0], ref[1])
    for doc in dm.items():
        if DocMod.is_in_dict(ref[1],doc[1]):
            print('\n\n\n############## Found Document Module Object #:', doc[0], '##############\n')
            DocMod.print_report(docmodreport, doc[1])
            handle = 'Document-' + doc[1]['dccDocHandleNo']
            
            docmatch[handle] = doc[1]
            
            # Construct a new PERM set for each handle entry
            if_not_in_pub_coll = PD.dict_crit_act(
                            {'NOT' : PD.chk_list(handle,pub_list,'eq')},
                            {'Action' : 'Message', 'Message' : '*** WARNING: Document is NOT in Published Collection ***'})

            if_in_pub_coll = PD.dict_crit_act(
                            PD.chk_list(handle,pub_list,'eq'),
                            {'Action' : 'Message', 'Message' : '*** Document IS in Published Collection ***'})


            SET_TMTPUBLISHED = {
                    'ObjSel'    : { 'Criteria' : PD.docORcol},
                    'ObjAct'    : [ PD.add_published_keyword,
                                    PD.chk_published_keyword,
                                    if_not_in_pub_coll,
                                    if_in_pub_coll],
                    'PermAct'   : [{'Criteria' : {}, 'Action' : {}}]} 
            
            PERM.check_perms(s, SET_TMTPUBLISHED, [handle], Ask = True)            
            docmodlist.append('Document-' + doc[1]['dccDocHandleNo'])
            

docmodreport = []
docmodreport.append('dccDocTitle')
docmodreport.append('dccDocNo')
docmodreport.append('dccDocRev')
docmodreport.append('dccDocVersionHyperlink')
docmodreport.append('dccDocSignedApproved')
docmodreport.append('TMTPublished')
docmodreport.append('dccStatusCheckDate')
docmodreport.append('dccDocHandleNo')

print('\n\n*********** Audit of documents in Published Collection ****************')
for dcc_doc in pub_list:
    if 'Document-' in dcc_doc:
        fd = DCC.prop_get(s, dcc_doc, InfoSet = 'DocBasic')
        fd['permissions'] = DCC.prop_get(s, dcc_doc, InfoSet = 'Perms')
        fd['versions'] = DCC.prop_get(s, dcc_doc, InfoSet = 'Versions')
        print('\n############## ', dcc_doc, '##############')
        if dcc_doc in docmodlist:
            DocMod.print_report(docmodreport, docmatch[dcc_doc])
            print('\n')
            DCC.print_doc_basic(fd)
            print('\n\t DCC View URL: ',Tree.url_view(fd['handle']),'\n')

            print('*** [', dcc_doc, '] is recorded as published in Document Module')
            if not 'TMTPublished' in fd['keywords']:
                print('*** WARNING: Document in Published Collection, but TMTPublished keyword is not set')
            docmod_title = docmatch[dcc_doc].get('dccDocTitle', 'No Attribute Value Assigned')
            if not fd['title'] == docmod_title:
                print('*** WARNING: Titles do not match')
                print('\tDCC Title: ', fd['title'])
                print('\tDocMod Title: ', docmod_title)
            docmod_ver = DCC.get_handle(docmatch[dcc_doc]['dccDocVersionHyperlink'])
            if not fd['versions']['prefver'] == docmod_ver:
                print('*** WARNING: Preferred Versions do not match')
                print('\tDCC Version Handle: ', fd['versions']['prefver'])
                print('\tDocMod Version Handle: ', docmod_ver)
            if not docmatch[dcc_doc]['dccDocNo'] in fd['tmtnum']:
                print('*** WARNING: TMT Document Numbers do not match')
                print('\tDCC Document Number (with revision): ', fd['tmtnum'])
                print('\tDocMod Document Number (without revision): ', docmatch[dcc_doc]['dccDocNo'])            
            if not docmatch[dcc_doc]['dccDocRev'] in fd['tmtnum']:
                print('*** WARNING: TMT Document Revisions do not match')
                print('\tDCC Document Number: ', fd['tmtnum'])
                print('\tDocMod Revision Number: ', docmatch[dcc_doc]['dccDocRev'])     
        else:   
            DCC.print_doc_basic(fd)
            print('\n\t DCC View URL: ',Tree.url_view(fd['handle']),'\n')
            
            if not 'TMTPublished' in fd['keywords']:
                print('*** WARNING: [', dcc_doc, '] is NOT recorded as published in Document Module')
            if not 'TMTPublished' in fd['keywords']:
                print('*** WARNING: Document is in DCC Configuration Control (Published) Collection, but TMTPublished keyword is not set')
