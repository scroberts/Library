#!/usr/bin/env python3

# external modules

# my modules
import DCC
import Config as CF

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
    

def iter_print_tree(s, tree, key, indent):
    branch = tree[key]
    for doc in branch['documents']:
        nameData = DCC.prop_get(s, doc, InfoSet = 'Title')
        print(indent+doc, ':', nameData['title']) 
    for other in branch['others']:
        nameData = DCC.prop_get(s, other, InfoSet = 'Title')
        print(indent+other, ':', nameData['title'])        
    for col in branch['collections']:
        nameData = DCC.prop_get(s, col, InfoSet = 'Title')
        print(indent+col, ':', nameData['title'])   
        iter_print_tree(s, tree, col, indent+'    ')

def build_tree(s, keyname, target, tree, **kwargs):
    # kwargs options:
    #  Exclude - List of handles to not be included in the tree
    
    excludeList = kwargs.get('Exclude',[])

    documents = []
    collections = []
    others = []
    dict = {}
    
    fd = DCC.prop_get(s, target, InfoSet = 'CollCont', Depth = '1')

    for idx,d in enumerate(fd):
        handle = d['name'][1]
        if not handle in excludeList:
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
        if not col in excludeList:
            tree = build_tree(s, col, col, tree, **kwargs)
    return(tree)
  
def print_tree(s,tree):
    iter_print_tree(s, tree, 'root', '')

def get_tree(s, collhandle, **kwargs):
    return(build_tree(s, collhandle, collhandle, build_root(collhandle), **kwargs))
    
def get_flat_tree(tree):
    fl = flat_tree(tree, 'root', [])    
    return(fl)
    
def build_root(collhandle):
    tree = {}
    tree['root'] = {'collections' : [collhandle], 'documents' : [], 'others' : []}
    return(tree)

def test_tree():
    collhandle = 'Collection-286'
    exclude = ['Collection-7337','Document-21244', 'Document-26018']

    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)

    print('excluding:',exclude)
    tree = get_tree(s, collhandle, Exclude = exclude)
    print_tree(s,tree)
    
    print('\n\n')
    for branch in tree:
        print(branch+': ',tree[branch])
        
    fl = flat_tree(tree, 'root', [])
    print(fl)
    
if __name__ == '__main__':
    print("Running module test code for",__file__)
    test_tree()


