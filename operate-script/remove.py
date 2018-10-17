# -*- coding:utf-8 -*-
# 矿机下架：
import json
import os
import sys
import time
import uuid

MINER_SCRIPT_PATH = './miner-script'


def get_mineprogram():
    """
    获取系统中所有的挖矿程序名称的列表
    """
    try:
        for root, dirs, files in os.walk(MINER_SCRIPT_PATH):
            return dirs
    except Exception:
        raise


def stop_mineprogram():
    """
    关闭所有的挖矿程序
    """
    try:
        mine_program = get_mineprogram()
        if not mine_program:
            print('No program to stop.')
            return

        for program in mine_program:
            lines = os.popen('ps -ef|grep ' + program)
            lines = lines.readlines()
            if len(lines) <= 3:
                continue

            for line in lines:
                if "python3 remove.py" not in line:
                    if line.find("grep " + program) != -1:
                        continue
                    vars = line.split()
                    pid = vars[1]           # get pid
                    os.system('kill ' + pid)
    except Exception as err:
        print(err)


if __name__ == '__main__':
    stop_mineprogram()

# def main(name):
#     lines = os.popen('ps -ef|grep ' + name)
#
#     def getMac():
#         node = uuid.getnode()
#         mac = uuid.UUID(int=node).hex[-12:]
#         return mac
#
#     status = "异常"
#     mac = getMac()
#     lines = lines.readlines()
#     if len(lines) == 3:
#         status = "下架"
#     for line in lines:
#         if "python3 remove.py" not in line:
#             if line.find("grep " + name) != -1:
#                 continue
#             vars = line.split()
#             pid = vars[1]  # get pid
#             out = os.system('kill ' + pid)
#             if out == 0:
#                 status = "下架"
#     try:
#         userid = sys.argv[2]
#         id = sys.argv[3]
#         str_ = {"id": id, "userid": userid, "operator_type": "remove", "status": status, "mac": mac,
#                 "time": time.time(), "program": name, "operate_name": "remove"}
#         json_info = json.dumps(str_)
#         time.sleep(0.5)
#         print(json_info)
#     except Exception as e:
#         print(e)
#
#
# if __name__ == '__main__':
#     print(sys.argv)
#     if len(sys.argv) < 4:
#         print("please input the params name")
#     else:
#         name = sys.argv[1]
#         main(name)
