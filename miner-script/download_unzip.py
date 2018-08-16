# -*- coding:utf-8 -*-
import os
import sys

def download(url):
    os.system("wget -c "+url)

def unzip(filename):
    os.system("tar -zxvf "+filename +" -C /opt/miner/bin/")

def main(url):
    filename = url.split('/')[-1]
    filename_ = filename.split(".")[0]
    path = "/opt/miner/bin/"+filename_
    isfile = os.path.isdir(path)
    if not isfile:
        download(url)
        unzip(filename)
    else:
        print("there is exist the file")

if __name__ == '__main__':
    if len(sys.argv)<2:
        print("please input the params name")
    else:
        url = sys.argv[1]
        main(url)