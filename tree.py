#!/usr/bin/env python3

# external modules

# my modules
import DCC
import config as cf

def flat_tree(tree, key, list):
    branch = tree[key]
    for doc in branch['documents']:
        list.append(doc)
    for other in branch['others']:
        list.append(other)
    for col in branch['collections']:
        list.append(col)
        flat_tree(tree, col, list)

    return(list)   
    

def iter_print_tree(tree, key, indent):
    branch = tree[key]
    for doc in branch['documents']:
        print(indent+doc) 
    for other in branch['others']:
        print(indent+other)
    for col in branch['collections']:
        print(indent+col)
        iter_print_tree(tree, col, indent+'    ')

def build_tree(s, keyname, target, tree):
    documents = []
    collections = []
    others = []
    dict = {}
    
    fd = DCC.getProps(s, target, InfoSet = 'Coll', Depth = '1')

    for idx,d in enumerate(fd):
        handle = d['name'][1]

        if idx == 0:
            dict['parent'] = handle
        else:
            if 'Document' in handle:
                documents.append(handle)
            elif 'Collection' in handle:
                collections.append(handle)
            else:
                others.append(handle)

    dict['collections'] = collections
    dict['documents'] = documents
    dict['others'] = others

    tree[keyname] = dict
    for col in collections:
        tree = build_tree(s, col, col, tree)
    return(tree)
  
def print_tree(tree):
    iter_print_tree(tree, 'root', '')

def get_tree(s, collhandle):
    return(build_tree(s, collhandle, collhandle, build_root(collhandle)))
    
def get_flat_tree(tree):
    fl = flat_tree(tree, 'root', [])    
    return(fl)
    
def build_root(collhandle):
    tree = {}
    tree['root'] = {'collections' : [collhandle], 'documents' : [], 'others' : []}
    return(tree)

def test_tree():
    collhandle = 'Collection-10259'

    # Login to DCC
    s = DCC.login(cf.dcc_url + cf.dcc_login)

    
    tree = get_tree(s, collhandle)
    print_tree(tree)
    
    print('\n\n')
    for branch in tree:
        print(branch+': ',tree[branch])
        
    fl = flat_tree(tree, 'root', [])
    print(fl)
    
if __name__ == '__main__':
    print("Running module test code for",__file__)
    test_tree()


