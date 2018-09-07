# -*- coding:utf-8 -*-
import os
import redis
from pykafka import KafkaClient
import uuid
import json
import time
import sys
import random

SYN = None

def main():
    def getMac():
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        return mac
    mac = getMac()
    producer = None
    try:
        # client = KafkaClient(hosts="47.106.253.159:9092")
        # topic = client.topics[b'operate']
        # producer = topic.get_producer()
        pool = redis.ConnectionPool(host='47.106.253.159', port='6379', db=0, password='sjdtwigkvsmdsjfkgiw23usfvmkj2')
        conn = redis.Redis(connection_pool=pool)
        ps = conn.pubsub()
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
        SYN = random.randint(0, 100000000)
        response = '{"taskid":'+id+', "action":"reboot", "maclist":['+mac+'], "result":'+json_info+', "syn": '+SYN+'}'
        conn.publish("BrokerMachineChannel", response)
        time.sleep(0.5)
        ps.subscribe("BrokerMachineChannel")
        for _item_ in ps.listen():
            if _item_['type'] == 'message':
                data = _item_['data']
                data = str(data, encoding='utf-8')
                message = json.loads(data)
                maclist = message['maclist']
                ack = message['ack']
                if mac in maclist and ack == SYN+1:
                    break
                else:
                    conn.publish("BrokerMachineChannel", response)
                    time.sleep(1)
            else:
                conn.publish("BrokerMachineChannel", response)
                time.sleep(1)
        # producer.produce(bytes(json_info, encoding="utf8"))
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