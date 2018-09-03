# -*- coding:utf-8 -*-
from pykafka import KafkaClient
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
                producer = None
                try:
                    client = KafkaClient(hosts="47.106.253.159:9092")
                    topic = client.topics[b'operate']
                    producer = topic.get_producer()
                    json_info = json.dumps(j)
                    producer.produce(bytes(json_info, encoding="utf8"))
                    f.close()
                    fb = open("/opt/reboot.txt",'w')
                    fb.truncate()
                    fb.close()
                except Exception as e:
                    print(e)
                finally:
                    producer.stop()

if __name__ == '__main__':
    main()