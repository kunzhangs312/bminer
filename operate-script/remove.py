# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import uuid
import os
import time
import json
import sys

def main(name):
    lines = os.popen('ps -ef|grep '+name)
    def getMac():
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        return mac
    status = "异常"
    mac = getMac()
    lines = lines.readlines()
    if len(lines)==3:status="下架"
    for line in lines:
        if "python3 remove.py" not in line:
            if line.find("grep "+name) != -1: continue
            vars = line.split()
            pid = vars[1]  # get pid
            print(pid)
            out = os.system('kill ' + pid)
            if out == 0:
                status = "下架"
    producer = None
    try:
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'operate']
        producer = topic.get_producer()
        userid = sys.argv[2]
        id = sys.argv[3]
        str_ = {"id":id,"userid":userid,"operator_type": "remove", "status": status, "mac": mac, "time": time.time(),"program":name,"operate_name":"remove"}
        json_info = json.dumps(str_)
        producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)
    except Exception as e:
        print(e)
    finally:
        producer.stop()

if __name__ == '__main__':
    if len(sys.argv)<4:
        print("please input the params name")
    else:
        name = sys.argv[1]
        main(name)