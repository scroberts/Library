#!/usr/bin/env python3

# external modules
import sys

# my modules
import Config as CF
import DCC
import FileSys

debug = False

def in_dict(key, val, dict, **kwargs):
    debug = False
# checks if key has a value that matches val
# kwargs:
#   Match = 'eq' or 'in'
#       eq means exact match (==)
#       in means in string (in)
    if debug: print('checking key = ', key, 'val = ', val)
    if debug: print('in dict = ',dict)
    match = kwargs.get('Match', 'eq')
    if not key in dict:
        if debug: print('key not in dict, returning False')
        return(False)
    if match == 'eq' and dict[key] == val:
        if debug: print('match eq = True')
        return(True)
    elif match == 'in' and val in dict[key]:
        if debug: print('match in = True')
        return(True)
    else:
        if debug: print('match = False')
        return(False)
        
def in_list(val, list, **kwargs):
# checks if key has a value that matches val
# kwargs:
#   Match = 'eq' or 'in'
#       eq means exact match (==)
#       in means in string (in)
    match = kwargs.get('Match', 'eq')
    for item in list:
        if match == 'eq' and item == val:
            return(True)
        elif match == 'in' and val in item:
            return(True)
    return(False)

def parse(p,dict):
    # p contains the criteria 
    # dict contains the dictionary to check
    # parse returns True if the criteria are met in the dictionary
    # parse expects a dictionary with on key.
    # the value will be either a dictionary or a list
#     key, val = next(iter(p.items()))
    for key, val in p.items():
        if key == 'AND':
            if debug: print('AND Parsing: val = ', val)
            # expects a list of dicts
            for d in val:
                if debug: print('AND Parsing: d = ', d)
                if not parse(d, dict):
                    return(False)
            return(True)
        if key == 'OR':
            # expects a list of dicts
            for d in val:
                if parse(d, dict):
                    return(True)
            return(False)
        if key == 'XOR':
            # XOR is true if only one input is true
            # expects a list of dicts
            count = 0
            for d in val:
                if parse(d, dict):
                    count += 1
            if count == 1:
                return(True)
            return(False)
        elif key == 'NOT':
            return(not parse(val, dict))
        elif key == 'InDict':
            k = val['key']
            v = val['val']
            m = val['match']
            if debug: print('checking k, v',k,v)
            return(in_dict(k, v, dict, Match = m))
        elif key == 'InList':
            v = val['val']
            l = val['list']
            m = val['match']
            return(in_list(v,l,Match = m))
        else:
            print('key = ', key)
            print('Error - key not found')
            sys.exit(1)

def test_in_list():
    list = ['Scott', 'Cameron', 'Roberts']
    print(in_list('Scott', list))
    print(in_list('Cam', list))
    print(in_list('Cam', list, Match = 'in'))

def test_parse():
    dict = {}
    dict['name'] = 'Scott Roberts'
    dict['home'] = 'Victoria' 
    dict['number'] = 42
    
    key = 'name'
    val = 'Scott'
    match = 'in'
    c = {'InDict' : {'key' : key, 'val' : val, 'match' : match}}
    key = 'home'
    val = 'V'
    match = 'in'
    d = {'InDict' : {'key' : key, 'val' : val, 'match' : match}}
    e = {'NOT' : d}
    f = {'NOT' : e}
    g = {'NOT' : f}
    h = {'AND' : [c,d]}
    print('c',parse(c, dict))
    print('d',parse(d, dict))   
    print('g',parse(g, dict))
    print('h',parse(h, dict))
    
#     list = ['Scott', 'Cameron', 'Roberts']
#     val = 'Camp'
#     j = {'InList' : {'list' : list, 'val' : val, 'match' : 'in'}}
#     print('j', parse(j))
        
def test_in_dict():
    dict = {}
    dict['name'] = 'Scott Roberts'
    dict['home'] = 'Victoria' 
    dict['number'] = 42
    
    print('Test 1:',in_dict('nokey','test', dict))
    print('Test 2:',in_dict('name','Scott', dict))
    print('Test 3:',in_dict('name','Scott Roberts', dict))
    print('Test 4:',in_dict('name','Scott Roberts', dict, Match = 'eq'))
    print('Test 5:',in_dict('name','Scott', dict, Match = 'in'))
    print('Test 6:',in_dict('name','Scott Roberts', dict, Match = 'bad'))
    
if __name__ == '__main__':
    print("Running module test code for",__file__)
#     test_in_dict()
    test_parse()
#     test_in_list()

