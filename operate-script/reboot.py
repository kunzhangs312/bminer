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
        client = KafkaClient(hosts="47.106.253.159:9092")
        topic = client.topics[b'operate']
        producer = topic.get_producer()
        userid = sys.argv[1]
        id = sys.argv[2]
        str_ = {"id": id, "userid": userid,"operator_type": "reboot", "status": "正在重启", "mac": mac, "time": time.time(),"program":None,"operate_name":"reboot"}
        json_info = json.dumps(str_)
        file = os.path.isfile("/opt/reboot.txt")
        if not file:
            os.mknod("/opt/reboot.txt")
            os.chmod("/opt/reboot.txt", 755)
        with open("/opt/reboot.txt","r+") as f:
            f.write(json_info)
        producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)
    except Exception as e:
        print(e)
    finally:
        producer.stop()
    os.system("reboot -h now")

if __name__ == '__main__':
    if len(sys.argv)<3:
        print("please input the params name")
    else:
        main()