# -*- coding:utf-8 -*-
import os
import uuid
import json
import time
import sys

def main():
    def getMac():
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        return mac
    mac = getMac()
    try:
        userid = sys.argv[1]
        id = sys.argv[2]
        str_ = {"id": id, "userid": userid,"operator_type": "reboot", "status": "成功", "mac": mac, "time": time.time(),"program":None,"operate_name":"reboot"}
        json_info = json.dumps(str_)
        print(json_info)
        time.sleep(2)
    except Exception as e:
        print(e)
    os.system("shutdown -h now")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("please input the params name")
    else:
        main()