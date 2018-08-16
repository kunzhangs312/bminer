# -*- coding:utf-8 -*-
import os
from pykafka import KafkaClient
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
    producer = None
    try:
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'operate']
        producer = topic.get_producer()
        userid = sys.argv[1]
        id = sys.argv[2]
        str_ = {"id": id, "userid": userid,"operator_type": "reboot", "status": "成功", "mac": mac, "time": time.time(),"program":None,"operate_name":"reboot"}
        json_info = json.dumps(str_)
        producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)
    except Exception as e:
        print(e)
    finally:
        producer.stop()
    os.system("shutdown -h now")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("please input the params name")
    else:
        main()