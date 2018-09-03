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

class Miner(threading.Thread):
    miner = None
    cmd = None
    env = None
    is_break = False
    mac = None
    producer = None
    coin = None

    def init(self, cmd, env={}):
        self.cmd = cmd
        new_env = os.environ.copy()
        new_env.update(env)
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
            time.sleep(60)
            self.get_miner_data()

    def get_miner_data(self):
        url = "http://127.0.0.1:8080/api/stats"
        try:
            response = requests.get(url)
            if response is not None:
                rsp = response.text
                data = json.loads(rsp)
                program_name  = "btm-miner"
                ret = []
                speed = 0
                for key,value in data.items():
                    id = key
                    hash = value["hashrate"]
                    hash = float('%.3f' % hash)
                    speed += hash
                    res_ = {"id": id, "info": None, "hash": hash, "temperature": None,
                            "gpu_power_usage": None, "fan": None}
                    ret.append(res_)
                speed = str(speed)+" Bhash/s"
                str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name,
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
        {"id":24774,"service_type":"MNX","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"BTM","Extra":"","IsManualPool":0,"Primary":{"CoinName":"btm","WalletAddress":"bm1qyum3xzqmn0cknvs734ae7y9vjysg8nydaxxpz6","PoolAddress":"btm.f2pool.com:9221","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = 'cd {}/btm-miner;./miner '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    Bin += "-url stratum+tcp://{} ".format(Primary['PoolAddress'])
    Bin += "-user {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    if len(config['Extra']) > 0:
        Bin += config['Extra']
    return Bin


def main():
    fpath = os.path.dirname(os.path.realpath(__file__))
    ch2dir = "{}/bin".format(fpath)
    cmdline = renderCmd(ch2dir)
    if not cmdline: return
    print(cmdline)
    miner = Miner()
    miner.init(cmdline)
    miner.init(cmdline, dict(LD_LIBRARY_PATH="$LD_LIBRARY_PATH:{}/btm-miner/cuda9".format(ch2dir)))
    miner.start()
    miner.join()

if __name__ == '__main__':
    main()









