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

grp_all_users = 'Group-4'
grp_Isbrucker = 'Group-536'
grp_SE_readership = 'Group-325'
grp_M1CS_obs = 'Group-641'

usr_sr_admin = 'User-1083'
usr_holly = 'User-21'
usr_site_admin = 'User-2'
usr_kyle = 'User-1087'
usr_lindquist = 'User-120'
usr_chylek = 'User-1165'
usr_peter_gray = 'User-383'
usr_christophe = 'User-1167'

user_handle = dic_handle_in('User-')
group_handle = dic_handle_in('Group-')

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

no_se_readership = {'NOT' : dic_handle_eq( grp_SE_readership )}

exclude_grp_se_readership = dic_handle_not_in(grp_SE_readership)
exclude_grp_all_users = dic_handle_not_in(grp_all_users)

REMOVE = {'Action' : 'Remove'}

add_R_grp_se_readership = {'Action' : 'Add', 'Handle' : grp_SE_readership, 'Perms' : {'Read' : 'True'}}

handle_sr_admin = dic_handle_eq('usr_sr_admin')


# Set A
obj_sel = {}
perm_sel = {}
obj_criteria_dict = {}
obj_actions_dict = {}


# Perms:
# A1: Remove any read_only users (they should be in groups)
perm_criteria_A1 = user_read_only
perm_actions_A1 = REMOVE

# A2: Remove read_only groups (except those in SE readership all)
perm_criteria_A2 = {'AND' : [group_read_only, no_se_readership]}
perm_actions_A2 = REMOVE

# A3: Remove group or user with no Read, but Write and/or Manage
perm_criteria_A3 = perm_W_or_M_no_R
perm_actions_A3 =  REMOVE

# A4: Add SE readership all if not already there
perm_criteria_A4 = no_se_readership
perm_actions_A4 = add_R_grp_se_readership

# A5: Change write with no read to RW
perm_criteria_A5 = perm_write_only
perm_actions_A5 = {'Action' : 'Change', 'Perms' : {'Read':True, 'Write':True}}

# perm_criteria_A? =
# perm_actions_A? =  

# setA =  {'ObjSel' : {'Criteria' : obj_sel},
#          'ObjAct' : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
#          'PermAct' : [{'Criteria' : perm_criteria_A2, 'Action' : perm_actions_A2}]}

setA =  {'ObjSel' : {'Criteria' : obj_sel},
         'ObjAct' : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
         'PermAct' : [{'Criteria' : perm_criteria_A1, 'Action' : perm_actions_A1},
                     {'Criteria' : perm_criteria_A2, 'Action' : perm_actions_A2},
                     {'Criteria' : perm_criteria_A3, 'Action' : perm_actions_A3},
                     {'Criteria' : perm_criteria_A4, 'Action' : perm_actions_A4},
                     {'Criteria' : perm_criteria_A5, 'Action' : perm_actions_A5}]}
                     

SE_read_OR_M1CS_obs = {'OR' : [dic_handle_eq(grp_SE_readership), dic_handle_eq(grp_M1CS_obs)]}

# SetB Remove Dumas user read only
# B1: Remove any read_only users (they should be in groups)
perm_criteria_B1 = {'AND' : [user_read_only, dic_handle_eq(usr_christophe)]}
perm_actions_B1 = REMOVE
setB =  {'ObjSel' : {'Criteria' : obj_sel},
         'ObjAct' : {'Criteria' : obj_criteria_dict, 'Action' : obj_actions_dict},
         'PermSel' : {'Criteria' : SE_read_OR_M1CS_obs },
         'PermAct' : [{'Criteria' : perm_criteria_B1, 'Action' : perm_actions_B1}]}
 


# print(setB)

# try:
#     perm_sel = setB['PermSel']['Criteria']
# except:
#     print('PerSel is not defined')
#         
# print('PerSel is defined', perm_sel)
# 
# # 
# print(setA['PermAct'])
# 
# for perm_act in setA['PermAct']:
#     print(perm_act)