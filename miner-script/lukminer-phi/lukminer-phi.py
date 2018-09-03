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
        self.miner = subprocess.Popen(self.cmd,shell=True,stdout=subprocess.PIPE,env=self.env)
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
        poller.register(self.miner.stdout,select.POLLIN)
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
    def stop(self):
        self.is_break = True

    def get_miner_data(self):
        url = "http://127.0.0.1:3333"
        res = requests.get(url)
        data = json.loads(res.text)
        program_name = "xmrig-amd"
        ret = []
        speed = str(data['hashrate']['highest']) +" Bhash/s"
        str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name, "coin": self.coin,
                "devices": ret}
        json_info = json.dumps(str_)
        if self.producer is None:
            self.producer = self.getProducer()
        self.producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)

    def getProducer(self):
        client = KafkaClient(hosts="47.106.253.159:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()

    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac

    def getCoin(self):
        json_conf = get_miner_config()
        self.coin = json_conf["Primary"]["CoinName"]

def get_miner_config():
    str = """
        {"id":24774,"service_type":"Zcash","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth","WalletAddress":"48LHRj3T9Jfeq87sikft1ijRzuGjo5w21ALP5gnvPeTkdqGgh2qQo7LXwKpuFDnoEUWhyHZrWsiuxVqHkAikyAuo1t9y5zE","PoolAddress":"xmr.f2pool.com:13531","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = 'echo 14000 > /proc/sys/vm/nr_hugepages; {}/lukminer-phi/luk-phi '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    if 'cryptonight' == config['Algorithm']:
        Bin += "-a xmr-v7 "
    else:
        Bin += "-a {} ".format(config['Algorithm'])
    Bin += "--user {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    Bin += "--host {} ".format(Primary['PoolAddress'].split(":")[0])
    Bin += "--port {} ".format(Primary['PoolAddress'].split(":")[1])
    Bin += "--pass x "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    return Bin + " 2>&1"

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