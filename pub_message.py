import redis
import time
import json
import sys

def getMac():
    import uuid
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return mac

if __name__ == '__main__':
    pool = redis.ConnectionPool(host='47.106.253.159', port='6379', db=0, password='sjdtwigkvsmdsjfkgiw23usfvmkj2')
    conn = redis.Redis(connection_pool=pool)
    mac = getMac()
    channel = mac[0:2]+"_miner_channel"
    data = {"mac":mac,"time":int(time.time()),"cmd":sys.argv[1]}
    message = json.dumps(data)
    conn.publish(channel,message)
    print(sys.argv[1])
