# -*- coding:utf-8 -*-
import os
from pykafka import KafkaClient
import uuid
import json
import time
import sys
import random
import redis

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
        str_ = {"id": id, "userid": userid,"operator_type": "reboot", "status": "成功", "mac": mac, "time": time.time(),"program":None,"operate_name":"reboot"}
        json_info = json.dumps(str_)
        # producer.produce(bytes(json_info, encoding="utf8"))
        SYN = random.randint(0, 100000000)
        response = '{"taskid":' + id + ', "action":"shutdown", "maclist":[' + mac + '], "result":' + json_info + ', "syn": ' + SYN + '}'
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
                if mac in maclist and ack == SYN + 1:
                    break
                else:
                    conn.publish("BrokerMachineChannel", response)
                    time.sleep(1)
            else:
                conn.publish("BrokerMachineChannel", response)
                time.sleep(1)
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