#!/usr/bin/env python3

# external modules

# my modules

def get_yn(question):
    ans = ''
    while (ans.upper() != 'Y') and (ans.upper() != 'N'):
        print(question,end="")
        ans = input()
    if ans.upper() == 'Y':
        return True
    return False

def remove_dict_from_list(thelist, key, value):
    thelist[:] = [d for d in thelist if d.get(key) != value]
    return(thelist)