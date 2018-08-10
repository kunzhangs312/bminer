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
import re

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
        READ_ONLY = (select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR)
        poller.register(self.miner.stdout, READ_ONLY)
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
        url = "http://127.0.0.1:3337/monitoring/management"
        try:
            res = requests.get(url)
            text = res.text
            program_name = "claymore-xmr"
            matchObj = re.search(r'Total Speed:.*?H/s', text)
            speed = None
            if matchObj:
                speed = matchObj.group().split("Total Speed:")[-1].strip()
            matchObj2 = re.search(r'{"result": .*?]}', text)
            ret = []
            if matchObj2:
                result = matchObj2.group()
                json_res = json.loads(result)
                result_arr = json_res["result"]
                id = result_arr[2].split(";")[-1]
                hash = result_arr[3]
                temperature = result_arr[6].split(";")[0]
                fan = result_arr[6].split(";")[1]
                info = self.getInfo(text,id)
                res_ = {"id": id, "info": info, "hash": hash, "temperature": temperature,
                       "gpu_power_usage": None,"fan":fan}
                ret.append(res_)
            str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name, "coin": self.coin,
                    "devices": ret}
            json_info = json.dumps(str_)
            if self.producer is None:
                self.producer = self.getProducer()
            self.producer.produce(bytes(json_info, encoding="utf8"))
            print(json_info)
        except Exception as e:
            print(e)

    def getInfo(self,text,id):
        info = None
        matchObj = re.search(r'GPU #'+id+':.*?available', text)
        if matchObj:
            info = matchObj.group().split(":")[-1]
        return info

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
    Bin = '{}/claymore-xmr/nsgpucnminer '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None
    Bin += "-xpool {} ".format(Primary['PoolAddress'])
    Bin += "-xwal {}.{} ".format(Primary['WalletAddress'], config['Worker'])
    Bin += "-mport 127.0.0.1:3337 "
    Bin += "-xpsw x "
    if len(config['Extra']) > 0:
        Bin += config['Extra']
    else:
        Bin += "-dbg -1 -wd 1 -colors 0 -pow7 1"
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