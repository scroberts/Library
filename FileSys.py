#!/usr/bin/env python3

# external modules
import os
import sys
from datetime import datetime
import time
import json

# my modules
import DCC
import Config as CF
import Tree

debug = False

# cacheMode Options
# NoDateCheck - if file exists it will be used
# NoCache - Cached files will be ignored
# Normal - Cached files will be used if determined valid
# All - All Cached Files will be used, even if validity cannot be determined (offline mode)

# cacheMode = ['NoDateCheck']
cacheMode = ['Normal']
# cacheMode = ['NoDateCheck', 'Normal']
# cacheMode = ['All']
# cacheMode = ['NoCache']

def check_date_okay(dccDate, osSecs):
    dccSecs = (datetime.strptime(dccDate,'%a, %d %b %Y %H:%M:%S %Z') - datetime(1970,1,1)).total_seconds()
    if dccSecs < osSecs:
        if debug: print('Cache date okay')
        return(True)
    if debug: print('Cache out of date')
    return(False)
    
def file_check_json(s, fname, path = CF.dccfilepath):
    if not '.json' in fname:
        fname = fname + '.json' 
    if not os.path.isfile(path+fname):
        return(False)
    if debug: print('File Exists')
    return(True)

def check_cache_okay(s, handle, fname, path = CF.dccfilepath):
    if not '.json' in fname:
        fname = fname + '.json' 
    if not os.path.isfile(path+fname):
        return(False)
    if debug: print('File Exists')
    if 'NoDateCheck' in cacheMode or 'All' in cacheMode:
        dccDate = "Sat, 01 Jan 2000 00:00:00 GMT"
    else:
        fd = DCC.prop_get(s, handle, InfoSet = 'DocDate')
        dccDate = fd['date']
    if not check_date_okay(dccDate, os.path.getctime(path+fname)):
        return(False)
    return(True)

def check_cache_fd_json(s, handle, infoSet, fname, path = CF.dccfilepath):
    if 'NoCache' in cacheMode:
        return([False], [])
        
    # Check if validity can be determined
    if 'Normal' in cacheMode:
        if infoSet in ['Children', 'CollCont', 'DocDate', 'Parents', 'Perms']:
            if debug: print('check_cache_fd_json: Returning False for InfoSet = ',infoSet)
            return([False, []])
                
    if not check_cache_okay(s, handle, fname):
        if debug: print('check_cache_fd_json - NOT okay in cache')
        return([False, []])
    if debug: print('check_cache_fd_json - IS okay in cache')
   
    fd = file_read_json(fname)
    if debug: print('Returning True from check_cache_fd_json')
    return([True, fd])
    
def test_cache():
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)
    handle = 'Collection-286' 
    fname = 'Collection-286_CollData'
    
    [flag, fd] = check_cache_fd_json(s, handle, 'CollData', fname)
    print(flag, fd)

def file_write_props(r, fname, path = CF.dccfilepath):
    if not '.html' in fname:
        fname = fname + '.html'
    webfile = open(CF.dccfilepath + fname,'wb')
    for chunk in r.iter_content(100000):
        webfile.write(chunk)
    webfile.close

def file_write_json(obj, fname, path = CF.dccfilepath):
    if not '.json' in fname:
        fname = fname + '.json'
    if debug: print('writing', path+fname)
    fh = open(path+fname,'w')
    json.dump(obj, fh)
    fh.close()
    
def file_read_json(fname, path = CF.dccfilepath):
    if not '.json' in fname:
        fname = fname + '.json'
    if debug: print('reading', path+fname)
    fh = open(path+fname,'r')
    obj = json.load(fh)
    fh.close
    return(obj)

def traverse(s, tr, collkey, dirpath = './', indent = '', **kwargs):
    # traverse follows the collection structure on the DCC and replicates it on the local disk
    pflag = False
    savefiles = kwargs.get('SaveFiles', False)
    exclude = kwargs.get('Exclude', [])        
    maxfilesize = kwargs.get('MaxFileSize', sys.maxsize)
        
    branch = tr[collkey]
    collist = branch['collections']
    doclist = branch['documents']
        
    cinfo = DCC.prop_get(s, collkey, InfoSet = 'CollData')
    print(indent,'Files in ', collkey, ': ', cinfo['title'])
    colname = cinfo['title']
    colname = colname.replace('/',' ')
    colname = colname.strip()
    dirpath = dirpath + colname + '/' 
    if savefiles:
        try:
            os.stat(dirpath)
        except:
            os.mkdir(dirpath) 
    for doc in doclist:
        finfo = DCC.prop_get(s, doc, InfoSet = 'DocBasic')
        print(indent + '\t',doc)
        title = finfo['title'].strip()
        print(indent + '\t\tTitle: ', title)
        print(indent + '\t\tFileName: ',finfo['filename'],' [',finfo['date'],']' ,' [', finfo['size'],' bytes ]')
        filedirpath = dirpath + title.replace('/',' ') + '/'
        filename = finfo.get('filename').strip()
        if doc in exclude:
        	print(indent + "\t\t\tFile is flagged to be excluded, will not download")
        else:
            if savefiles:
                try:
                    os.stat(filedirpath)
                except:
                    try:
                        os.mkdir(filedirpath)
                    except:
                        print('Error - could not create directory:', filedirpath)
                        sys.exit(0)
                
            if not os.path.isfile(filedirpath+filename):
                print(indent + "\t\t\tFile doesn't exist")
                if savefiles:
                    if finfo['size'] < maxfilesize:
                        print(indent + "\t\t\tGetting file")
                        DCC.file_download(s, doc, filedirpath, finfo['filename'])
                    else:
                        print(indent + "\t\t\tFile size exceeds MaxFileSize of ", maxfilesize, "bytes")
                else:
                    print(indent + "\t\t\tSaveFiles is False, so file will not be downloaded")


            elif (datetime.strptime(finfo['date'],'%a, %d %b %Y %H:%M:%S %Z') - datetime(1970,1,1)).total_seconds() > os.path.getctime(filedirpath+filename):
                print(indent + "\t\t\tFile exists, but is out of date:", time.ctime(os.path.getctime(filedirpath+filename)))
                if savefiles:
                    if finfo['size'] < maxfilesize:
                        print(indent + "\t\t\tGetting updated file")
                        DCC.file_download(s, doc, filedirpath, finfo['filename'])
                    else:
                        print(indent + "\t\t\tFile size exceeds MaxFileSize of ", maxfilesize, "bytes")
                else:
                    print(indent + "\t\t\tSaveFiles is False, so file will not be downloaded")
            else:
                print(indent + "\t\t\tFile exists, created:", time.ctime(os.path.getctime(filedirpath+filename)))

    for c in collist:
        if (not c == collkey) and (not c in exclude):
            traverse(s, tr, c, dirpath, indent + '\t', **kwargs)

def create_DCC_mirror(s, dcc_handle, dirpath, **kwargs):
    tr = Tree.get_tree(s,dcc_handle)
    Tree.print_tree(s, tr)
    docList = Tree.get_flat_tree(tr)
    traverse(s, tr, tr['root']['collections'][0], dirpath, **kwargs)
    
            
def testTraverse():
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)

    coll = 'Collection-286'    
    create_DCC_mirror(s, coll, '/Users/sroberts/Box Sync/TMT DCC Files/Test/', SaveFiles = True, MaxFileSize = 2000000)
    
if __name__ == '__main__':
    print("Running module test code for",__file__)
    test_cache()   
#     testTraverse()