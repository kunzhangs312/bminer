# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import subprocess
import select
import time
import uuid
import json
import threading
import os
import socket

class Miner(threading.Thread):
    miner = None
    cmd = None
    env = None
    is_break = False
    mac = None
    producer = None
    coin = None

    def init(self, cmd):
        self.cmd = cmd
        new_env = os.environ.copy()
        self.env = new_env
        self.env["GPU_FORCE_64BIT_PTR"] = "1"
        self.env["GPU_USE_SYNC_OBJECTS"] = "1"
        self.env["GPU_MAX_ALLOC_PERCENT"] = "100"
        self.env["GPU_SINGLE_ALLOC_PERCENT"] = "100"
        self.env["GPU_MAX_HEAP_SIZE"] = "10"
        if self.mac is None:
            self.getMac()
        if self.producer is None:
            self.getProducer()
        if self.coin is None:
            self.getCoin()

    def run(self):
        self.miner = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, env=self.env)
        if not self.miner:
            print("miner not started")
            return
        try:
            self.process()
        except Exception as e:
            print(e)
            self.miner.kill()

    def process(self):
        poller = select.poll()
        poller.register(self.miner.stdout, select.POLLIN)
        while True:
            ret_code = self.miner.poll()
            if ret_code is not None:
                print("miner has exit: {}".format(ret_code))
                return
            if self.is_break:
                print("miner stoped")
                self.miner.kill()
                return
            time.sleep(60)
            self.get_miner_data()

    def get_miner_data(self):
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.settimeout(3)
        try:
            tcp_client.connect(('127.0.0.1', 3335))
            tcp_client.send(b'devs|0')
            buf = tcp_client.recv(10240)
            buf = str(buf,encoding='utf-8')
            ret = []
            speed = 0
            program_name = "sgminer"
            for i in buf.split('|')[1:-1]:
                id = i.split(',')[0].split('=')[1]
                hash = int(i.split(',')[13].split('=')[1]) / 1024
                hash = float('%.2f' % hash)
                speed += hash
                temperature = i.split(',')[3].split('=')[1]
                fan = i.split(',')[5].split('=')[1]
                info = None
                gpu_power_usage = i.split(',')[10].split('=')[1]
                res_ = {"id": id, "info": info, "hash": hash, "temperature": temperature,
                        "gpu_power_usage": gpu_power_usage, "fan": fan}
                ret.append(res_)
            speed = str(speed)+" Mhash/s"
            str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name,
                    "coin": self.coin,
                    "devices": ret}
            json_info = json.dumps(str_)
            if self.producer is None:
                self.producer = self.getProducer()
            self.producer.produce(bytes(json_info, encoding="utf8"))
            print(json_info)
        except Exception as e:
            print(e)
        tcp_client.close()

    def getCoin(self):
        json_conf = get_miner_config()
        self.coin = json_conf["Primary"]["CoinName"]

    def stop(self):
        self.is_break = True

    def getProducer(self):
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()

    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac

def get_miner_config():
    str = """
        {"id":24774,"service_type":"RVN","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"x16r","Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth","WalletAddress":"RWoSZX6j6WU6SVTVq5hKmdgPmmrYE9be5R","PoolAddress":"raven.f2pool.com:3636","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/sgminer-x16r/sgminer '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    Bin += "-o stratum+tcp://{} ".format(Primary['PoolAddress'])
    Bin += "-u {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    Bin += "-p x --api-listen --api-port 3335 -T "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    else:
        Bin += '-I 19 -k {}'.format(config['Algorithm'])
    return Bin


def main():
    fpath = os.path.dirname(os.path.realpath(__file__))
    ch2dir = "{}/bin".format(fpath)
    cmdline = renderCmd(ch2dir)
    if not cmdline: return
    miner = Miner()
    miner.init(cmdline)
    miner.start()
    miner.join()

if __name__ == '__main__':
    main()