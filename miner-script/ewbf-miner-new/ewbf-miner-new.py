# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import subprocess
import select
import time
import uuid
import json
import threading
import os
import requests
import sys

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
        url = "http://127.0.0.1:3333/getstat"
        try:
            response = requests.get(url)
            text = response.text
            if text is not None:
                data = json.loads(text)
                speed = 0
                ret = []
                program_name = "ewbf-miner-new"
                for item in data.get('result', []):
                    hash = item.get('speed_sps', 0)
                    speed += hash
                    info = item.get('name', 0)
                    id = item.get('gpuid', 0)
                    temperature = item.get('temperature', 0)
                    gpu_power_usage = item.get('gpu_power_usage', 0)
                    res = {"id": id, "info": info, "hash": hash, "temperature": temperature,
                           "gpu_power_usage": gpu_power_usage}
                    ret.append(res)
                speed = str(speed) + " Bsol/s"
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
        {"id":24774,"service_type":"AION","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"AION","Extra":"","IsManualPool":0,"Primary":{"CoinName":"zec","WalletAddress":"0xa0c238f3b427320e5231e8703335fe52620895b08ded92fcd05f9775698bc321","PoolAddress":"aion.f2pool.com:6677","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"MiningType":"dcr","CoinName":"","WalletAddress":"DsUwCypjp9kpgzpz5dWhdewoXHYLNCHNqWQ","PoolAddress":"dcr.uupool.cn:3252","PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/ewbf-miner-new/miner '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    Bin += "--server {} ".format(Primary['PoolAddress'].split(":")[0])
    Bin += "--port {} ".format(Primary['PoolAddress'].split(":")[1])
    Bin += "--user {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    Bin += "--pass x --api 127.0.0.1:3333 "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    elif config['Algorithm'] == 'mnx':
        Bin += "--eexit 1 --algo 96_5 --pers ZcashPoW"
    else:
        Bin += "--eexit 1 --algo aion"
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
    if len(sys.argv)<2:
        print("please input the params name")
    else:
        main()
