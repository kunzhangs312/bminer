# -*- coding:utf-8 -*-
import json
import os
import time

def main():
    file = os.path.isfile("/opt/reboot.txt")
    if file:
        with open("/opt/reboot.txt","r+") as f:
            line = f.readline()
            if line is not None:
                j = json.loads(line)
                j['status'] = '正常'
                j['time'] = time.time()
                try:
                    json_info = json.dumps(j)

                    f.close()
                    fb = open("/opt/reboot.txt",'w')
                    fb.truncate()
                    fb.close()
                except Exception as e:
                    print(e)

if __name__ == '__main__':
    main()