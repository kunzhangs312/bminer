from pykafka import KafkaClient
from pykafka.simpleconsumer import OffsetType
import json
import redis

if __name__ == '__main__':
    pool = redis.ConnectionPool(host='localhost', port='6379', db=0,password='sjdtwigkvsmdsjfkgiw23usfvmkj2')
    conn = redis.Redis(connection_pool=pool)
    client = KafkaClient(hosts="192.168.0.69:9092")
    topic = client.topics[b'monitor']
    consumer = topic.get_balanced_consumer(
        consumer_group=b"master_consumer",  # 自己命令
        auto_offset_reset=OffsetType.LATEST,  # 在consumer_group存在的情况下，设置此变量，表示从最新的开始取
        zookeeper_connect='localhost:2181'
    )
    consumer.consume()
    consumer.commit_offsets()
    for message in consumer:
        if message is not None:
            value = message.value
            if value is not None:
                value = value.decode()
                if value is not None:
                    info = json.loads(value)
                    if info is not None and 'mac' in info:
                        mac = info['mac']
                        conn.hset("monitor_info",mac,info)
