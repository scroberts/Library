#!/usr/bin/env python3

# external modules
import re

# my modules

def strip_xml(mystring):
    return(re.sub('<[^>]*>', '', mystring))

def get_all_none_indiv(question):
    # Expects one of the following:
    #   'A' = 'All'
    #   'N' = 'None'
    #   'I' = 'Individual Y/N'
    #   Returns 'All', 'None' or 'Individual'
    ans = ''
    while (ans.upper() != ('A' or 'N' or 'I')):
        print(question,end="")
        ans = input()
        if ans.upper() == 'A':
            return 'All'
        elif ans.upper() == 'N':
            return 'None'
        elif ans.upper() == 'I':
            return 'Individual'
    
def get_yn(question):
    ans = ''
    while (ans.upper() != 'Y') and (ans.upper() != 'N'):
        print(question,end="")
        ans = input()
    if ans.upper() == 'Y':
        return True
    return False

def remove_dict_from_list(thelist, key, value):
    # removes dictionaries containing the supplied key/value from a list of dictionaries
    # note that lists are passed by reference so the input list is changed
    thelist[:] = [d for d in thelist if d.get(key) != value]
    
def mod_dict_in_list(thelist, checkkey, checkvalue, changekey, changevalue):
    # modifies entries in a list of dictionaries based on check criteria
    outlist = []
    for d in thelist:
        if checkkey in d.keys():
            if d[checkkey] == checkvalue:
                d[changekey] = changevalue
        outlist.append(d)
    return(outlist)
    
    
def test_mod():
    mylist = [{'name':'scott'}, {'name':'roberts'}]
    outlist = mod_dict_in_list(mylist, 'name', 'scott', 'flag', False)
    print(outlist)
    
def test_strip():
    mystring = '<p>Desc of test collection.</p><p>&nbsp;</p>'
    print(strip_xml(mystring))
    

if __name__ == '__main__':
    print("Running module test code for",__file__)
    test_mod()
    test_strip()
                
