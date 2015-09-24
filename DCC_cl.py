#!/usr/bin/env python3

# external modules
import DCC
import sys

# my modules
import Config as CF

debug = False

def copy_object(s):
    obj = input("Enter Object Handle: ")
    col = input("Enter Collection Handle to Copy To: ")
    DCC.add_docs_2_collections(s,[obj],[col])
    return

def main():
    # Login to DCC
    s = DCC.login(CF.dcc_url + CF.dcc_login)
    
    while True:
        com = input("Enter Command: ")
        if com.strip() == '':
            print('Exiting')
            break
        if com.upper() == 'COPY':
            copy_object(s)
        
if __name__ == '__main__':
    print("Running module test code for",__file__)
    main()