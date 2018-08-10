import redis
import json
import time
import os

def getMac():
    import uuid
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return mac

def process(mac0, data):
    data = str(data,encoding='utf-8')
    message = json.loads(data)
    mac = message['mac']
    time_ = message['time']
    cmd = message['cmd']
    if mac0 == mac:
        # set a timeout 5 min
        now = int(time.time())
        timeout = now-time_
        if timeout<5*60 :
            os.system(cmd)

if __name__ == '__main__':
    pool = redis.ConnectionPool(host='192.168.0.69', port='6379', db=0, password='sjdtwigkvsmdsjfkgiw23usfvmkj2')
    conn = redis.Redis(connection_pool=pool)
    mac = getMac()
    channel = mac[0:2] + "_miner_channel"
    ps = conn.pubsub()
    ps.subscribe(channel)
    for item in ps.listen():
        if item['type'] == 'message':
            data = item['data']
            if data is not None:
                process(mac,data)