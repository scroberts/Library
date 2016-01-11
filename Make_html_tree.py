#!/usr/bin/env python3

# external modules

# my modules
import Tree
import DCC


# Login to DCC
s = DCC.login(Site = 'Production')

# This utility creates an html report of the content below the specified collection

# froot = 'B. Enclosure Pre-Preliminary Design and Requirements Phase'
# coll = 'Collection-2219'

# froot = 'C. Enclosure Preliminary Design Phase'
# coll = 'Collection-2219'

coll = 'Collection-10598'
froot = coll

tr = Tree.return_tree(s, coll, froot)
Tree.html_tree(s,tr,froot)