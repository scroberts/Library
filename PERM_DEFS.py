#!/usr/bin/env python3

# external modules

# my modules

debug = False

# Data structure definition:
# ObjSel : will the criteria and actions be applied to this object?
#   Criteria : Object Selection Criteria
# ObjAct : dictionary containing object criteria and actions
#   Criteria : object change criteria. If met changes will be made to objects
#   Action : object change actions
# PermAct : dictionary containing permissions criteria and actions
#   Criteria : permission change criteria. If met changes will be made to permissions
#   Action : permission change actions
# 
# crit_act_set = {'obj_sel' : parse_dict, 
#             'obj' : [ list of dicts of {'obj_crit' : parse_dict, 'obj_act' : obj_act_dict}, {...} ]
#             'perm' : [ list of dicts of {'perm_crit' : parse_dict , 'perm_act' : perm_act_dict}, {...} ]  

def def_perm(k,v,m): return({'InDict' : {'key' : k, 'val' : v, 'match' : m}})

def dic_handle_eq(hdl): return(def_perm('handle',hdl,'eq'))
def dic_handle_in(hdl): return(def_perm('handle',hdl,'in'))
def dic_handle_not_eq(hdl): return({'NOT' : dic_handle_eq(hdl)})
def dic_handle_not_in(hdl): return({'NOT' : dic_handle_in(hdl)})
def make_permact(criteria, action): return({'Criteria' : criteria, 'Action' : action})

grp_all_users = 'Group-4'
grp_all_noEAR = 'Group-33'
grp_Isbrucker = 'Group-536'
grp_SE_readership = 'Group-325'
grp_M1CS_obs = 'Group-641'
grp_STR_managers = 'Group-655'

usr_sr_admin = 'User-1083'
usr_holly = 'User-21'
usr_site_admin = 'User-2'
usr_lindquist = 'User-120'
usr_peter_gray = 'User-383'
usr_christophe = 'User-1167'
usr_matthias = 'User-18'
usr_crampton = 'User-38'
usr_lianqi = 'User-407'

# IRIS Subsystem Team Members
usr_wright = 'User-753'
usr_larkin = 'User-218'
usr_moore = 'User-458'
usr_ryugi = 'User-572'
usr_lu = 'User-556'

# structures group
usr_szeto = 'User-138'
usr_chylek = 'User-1165'
usr_amir = 'User-573'
usr_kyle = 'User-1087'

user_handle = dic_handle_in('User-')
group_handle = dic_handle_in('Group-')

doc_handle = dic_handle_in('Document-')
col_handle = dic_handle_in('Collection-')
docORcol = {'OR' : [doc_handle, col_handle]}

SE_doc = def_perm('tmtnum', '.SEN.', 'in')
STR_doc = def_perm('tmtnum', '.STR.', 'in')
CTR_doc = def_perm('tmtnum', '.CTR.', 'in')
OPT_doc = def_perm('tmtnum', '.OPT.', 'in')
TEL_doc = def_perm('tmtnum', '.TEL.', 'in')

INS_doc = def_perm('tmtnum', '.INS.', 'in')

TELDEPT_doc = {'OR' : [STR_doc, CTR_doc, OPT_doc, TEL_doc]}

read_true = def_perm('Read', True, 'eq')
write_true = def_perm('Write', True, 'eq')
manage_true = def_perm('Manage', True, 'eq')
# The following will work correctly if the perm keys are not defined (i.e. no Write key means Write False)
read_false = {'NOT' : read_true}
write_false = {'NOT' : write_true}
manage_false = {'NOT' : manage_true}

user_read_only = {'AND' : [user_handle, read_true, write_false, manage_false]}
group_read_only = {'AND' : [group_handle, read_true, write_false, manage_false]}
perm_none = {'AND' : [read_false, write_false, manage_false]}
perm_write_only = {'AND' : [read_false, write_true, manage_false]}
perm_W_or_M_no_R = {'AND' : [read_false, {'OR' : [write_true, manage_true]}]}
user_manage_false = {'AND' : [user_handle, manage_false]}

no_se_readership = {'NOT' : dic_handle_eq( grp_SE_readership )}
no_str_managers = {'NOT' : dic_handle_eq( grp_STR_managers )}
se_readership_noRead_or_WM = {'AND' : [dic_handle_eq(grp_SE_readership), {'OR' : [read_false, write_true, manage_true]}]}

exclude_grp_se_readership = dic_handle_not_in(grp_SE_readership)
exclude_grp_all_users = dic_handle_not_in(grp_all_users)

REMOVE = {'Action' : 'Remove'}
CHANGE_R = perm_actions_A5 = {'Action' : 'Change', 'Perms' : {'Read':True}}

add_R_grp_se_readership = {'Action' : 'Add', 'Handle' : grp_SE_readership, 'Perms' : {'Read' : True}}
add_RWM_grp_str_managers = {'Action' : 'Add', 'Handle' : grp_STR_managers, 'Perms' : {'Read' : True, 'Write' : True, 'Manage' : True}}

handle_sr_admin = dic_handle_eq('usr_sr_admin')

# Set A
obj_sel = {}
perm_sel = {}
obj_criteria_dict = {}
obj_actions_dict = {}

# PermAct definitions
# Remove any read_only users (they should be in groups)
PERMACT_REMOVE_ro_users = make_permact(user_read_only, REMOVE)

# Remove read_only groups (except SE readership all)
PERMACT_REMOVE_ro_groups_except_se_reader = make_permact({'AND' : [group_read_only, no_se_readership]}, REMOVE)

# Remove group or user with no Read, but Write and/or Manage
PERMACT_REMOVE_grp_usr_perm_W_or_M_no_R = make_permact(perm_W_or_M_no_R, REMOVE)

# Change permissions to add Read in cases where there is Write Only
PERMACT_CHANGE_W_to_RW = make_permact(perm_write_only, {'Action' : 'Change', 'Perms' : {'Read':True, 'Write':True}})

# Add SE readership all if not already there
PERMACT_ADD_se_readership = make_permact(no_se_readership, add_R_grp_se_readership)

# Add STR Managers all if not already there
PERMACT_ADD_str_managers = make_permact(no_str_managers, add_RWM_grp_str_managers)

# Change SE readership no read or write/manage to read only
PERMACT_CHANGE_se_readership_RO = make_permact(se_readership_noRead_or_WM, CHANGE_R)

# Remove Individual users
def remove_user(user): return(make_permact(dic_handle_eq(user), REMOVE))

PERMACT_REMOVE_dumas_ro = make_permact({'AND' : [user_read_only, dic_handle_eq(usr_christophe)]}, REMOVE)
PERMACT_REMOVE_mathias_manage_false = make_permact({'AND' : [manage_false, dic_handle_eq(usr_matthias)]}, REMOVE)
# PERMACT_REMOVE_szeto = make_permact(dic_handle_eq(usr_szeto), REMOVE)
PERMACT_REMOVE_szeto = remove_user(usr_szeto)

usr_str_managers = {'OR' : [dic_handle_eq(usr_chylek), dic_handle_eq(usr_amir), dic_handle_eq(usr_kyle)]}

SET_REMOVE_UNNEEDED = {
        'ObjSel'    : { 'Criteria' : docORcol},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [ PERMACT_REMOVE_ro_users,
                        PERMACT_REMOVE_ro_groups_except_se_reader,
                        PERMACT_REMOVE_grp_usr_perm_W_or_M_no_R]}

SET_SE_READERSHIP = {
        'ObjSel'    : { 'Criteria' : docORcol},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [ PERMACT_ADD_se_readership,
                        PERMACT_CHANGE_se_readership_RO,
                        PERMACT_REMOVE_ro_users,
                        PERMACT_REMOVE_ro_groups_except_se_reader,
                        PERMACT_REMOVE_grp_usr_perm_W_or_M_no_R,
                        remove_user(grp_all_noEAR)]} 
                        
SET_IRIS_REMOVEUSERS_1 = {
        'ObjSel'    : { 'Criteria' : docORcol},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [ remove_user(usr_site_admin),
                        remove_user(usr_chylek),
                        remove_user(usr_crampton),
                        remove_user(usr_holly),
                        remove_user(grp_all_users)]}

SET_IRIS_REMOVEUSERS_2 = {
        'ObjSel'    : { 'Criteria' : docORcol},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [ remove_user(usr_matthias),
                        remove_user(usr_lianqi)]}      
                        
SET_IRIS_REMOVE_MATTHIAS_MANAGE_FALSE = {
        'ObjSel'    : { 'Criteria' : docORcol},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [ PERMACT_REMOVE_mathias_manage_false ]}                   

SET_IRIS_REMOVE_ISBRUCKER = {
        'ObjSel'    : { 'Criteria' : {'AND': [doc_handle, {'NOT' : INS_doc}]}},
        'ObjAct'    : { 'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermAct'   : [remove_user(grp_Isbrucker)]} 

SE_read_OR_M1CS_obs = {'OR' : [dic_handle_eq(grp_SE_readership), dic_handle_eq(grp_M1CS_obs)]}

SET_M1CS_PDR = {
        'ObjSel'    : {'Criteria' : docORcol},
        'ObjAct'    : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermSel'   : {'Criteria' : SE_read_OR_M1CS_obs},
        'PermAct'   : [PERMACT_REMOVE_dumas_ro,
                       PERMACT_REMOVE_szeto]}
                       
# For STR group documents, add group 'structure managers'.
# Remove members of structure managers group from individual permissions.
SET_STR_MANAGERS = {
        'ObjSel'    : {'Criteria' : STR_doc},
        'ObjAct'    : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermSel'   : {'Criteria' : usr_str_managers},
        'PermAct'   : [ PERMACT_ADD_str_managers,
                        remove_user(usr_chylek),
                        remove_user(usr_amir),
                        remove_user(usr_kyle),                        
                        ]}
                        
# For non-STR, optics and controls group documents, remove group 'structure managers'.
# Remove members of structure managers group from individual permissions.
SET_REMOVE_STR_MANAGERS = {
        'ObjSel'    : {'Criteria' : {'AND' : [docORcol, {'NOT' : TELDEPT_doc}]}},
        'ObjAct'    : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
        'PermSel'   : {'Criteria' : usr_str_managers},
        'PermAct'   : [ remove_user(usr_chylek),
                        remove_user(usr_amir),
                        remove_user(usr_kyle),                        
                        ]}
