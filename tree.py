#!/usr/bin/env python3

# external modules

# my modules
import DCC
import config as cf

def print_tree(tree, parent, indent):
    print(indent+parent)
    for branch in tree:
        if branch['parent'] == parent:
            for col in branch['collections']:
                print_tree(tree, col, indent+'    ')
            for doc in branch['documents']:
                print(indent+'    '+doc) 

        

def build_tree(s, target, tree):
    fd = DCC.getProps(s, target, InfoSet = 'Coll', Depth = '1')

    documents = []
    collections = []
    other = []
    dict = {}

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
                other.append(handle)

    dict['collections'] = collections
    dict['documents'] = documents
    dict['other'] = other

    print(dict)
    tree.append(dict)
    for col in collections:
        tree = build_tree(s, col, tree)
    return(tree)

target = 'Collection-286'

# Login to DCC
s = DCC.login(cf.dcc_url + cf.dcc_login)

tree = []
tree = build_tree(s, target, tree)

print_tree(tree, tree[0]['parent'], '')
    




