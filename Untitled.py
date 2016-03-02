#!/usr/bin/env python3
import CID

#M1CS CID Information
dirpath = r'/Users/paulb/Documents/TMT/Python/CID/CID M1CS/'
CID_coll = 'Collection-11006'
htmlfile = 'M1CS PDR CID DRF02 Scott.htm'
outroot = 'M1CS_'


CID.make_cid(dirpath, CID_coll, htmlfile, outroot)
