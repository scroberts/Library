#!/usr/bin/env python3

# external modules

# my modules
import DCC
import config as cf

def print_tree(tree, key, indent):
    branch = tree[key]
    for col in branch['collections']:
        print(indent+col)
        print_tree(tree, col, indent+'    ')
    for doc in branch['documents']:
        print(indent+doc) 
    for other in branch['others']:
        print(indent+other)
        

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
    
    
def build_root(collhandle):
    tree = {}
    tree['root'] = {'collections' : [collhandle], 'documents' : [], 'others' : []}
    return(tree)

def test_tree():
    collhandle = 'Collection-10259'

    # Login to DCC
    s = DCC.login(cf.dcc_url + cf.dcc_login)

    tree = build_tree(s, collhandle, collhandle, build_root(collhandle))
    
    print_tree(tree, 'root', '')
    
    print('\n\n')
    for branch in tree:
        print(branch+': ',tree[branch])
    
if __name__ == '__main__':
    print("Running module test code for",__file__)
    test_tree()


