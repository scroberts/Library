#!/usr/bin/env python3

import Tree
import DCC

# This script can be used to create an html list and a spreadsheet of documents below the
# specified collection.  The main use of the code is to create CID lists in html and spreadsheet
# from from a set of collections containing CID files


froot = 'Listing of STR CID'
coll = 'Collection-10669'

# Login to DCC
s = DCC.login(Site = 'Production') 

tr = Tree.return_tree(s, coll, froot)
Tree.xls_tree(s,tr,coll,froot)
Tree.html_tree(s,tr,froot)