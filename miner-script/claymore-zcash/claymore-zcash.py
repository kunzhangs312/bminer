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
            time.sleep(6)
            self.get_miner_data()

    def get_miner_data(self):
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.settimeout(3)
        try:
            tcp_client.connect(('127.0.0.1', 3333))
            tcp_client.send(b'{"id":0, "jsonrpc":"2.0", "method":"miner_getstat1"}')
            buf = tcp_client.recv(10240)
            buf = str(buf,encoding='utf-8')
            if len(buf)>30:
                rsp = json.loads(buf)
                primary_str = rsp['result'][3]
                primary = primary_str.split(';')
                temp_fan_str = rsp['result'][6]
                temp_fan = temp_fan_str.split(',')
                ret = []
                speed = 0
                program_name = "claymore"
                for i in range(len(primary)):
                    hash = primary[i]
                    hash = float(int(hash)/1024)
                    hash = float('%.3f' % hash)
                    speed += hash
                    id = i
                    temperature = None;fan = None
                    if len(temp_fan)>i:
                        temperature = temp_fan[i].split(";")[0]
                        fan = temp_fan[i].split(";")[1]

                    res_ = {"id": id, "info": None, "hash": hash,"temperature": temperature,
                            "gpu_power_usage": None, "fan": fan}
                    ret.append(res_)
                speed = str(speed)+" /s"
                str_ = {"mac": self.mac, "time": time.time(), "speed": speed,"program_name": program_name,
                        "coin": self.coin, "devices": ret}
                json_info = json.dumps(str_)
                if self.producer is None:
                    self.producer = self.getProducer()
                self.producer.produce(bytes(json_info, encoding="utf8"))
                print(json_info)
        except Exception as e:
            print(e)

    def stop(self):
        self.is_break = True

    def getCoin(self):
        json_conf = get_miner_config()
        self.coin = json_conf["Primary"]["CoinName"]

    def getProducer(self):
        client = KafkaClient(hosts="47.106.253.159:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()

    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac

def get_miner_config():
    str = """
        {"id":24774,"service_type":"ZEC","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"BTM","Extra":"","IsManualPool":0,"Primary":{"CoinName":"zec","WalletAddress":"t1ScBNXAYvETczSiA33XJz9omQNPXsWSBUU","PoolAddress":"zec.f2pool.com:3357","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"MiningType":"dcr","CoinName":"","WalletAddress":"DsUwCypjp9kpgzpz5dWhdewoXHYLNCHNqWQ","PoolAddress":"dcr.uupool.cn:3252","PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/claymore-zcash/zecminer64 '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    Bin += "-zpool {} ".format(Primary['PoolAddress'])
    Bin += "-zwal {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    Bin += "-zpsw x "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    else:
        Bin += "-dbg -1 -wd 1 -colors 0 -allpools 1"
    return Bin

def main():
    fpath = "/opt/miner"
    ch2dir = "{}/bin".format(fpath)
    cmdline = renderCmd(ch2dir)
    if not cmdline: return
    print(cmdline)
    miner = Miner()
    miner.init(cmdline)
    miner.start()
    miner.join()

if __name__ == '__main__':
    main()
