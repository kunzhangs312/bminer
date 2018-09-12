# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import uuid
import threading
import os
import subprocess
import select
import requests
import json
import time

class Miner(threading.Thread):
    miner = None
    cmd = None
    env = None
    is_break = False
    mac = None
    producer = None

    def init(self, cmd):
        self.cmd = cmd
        new_env = os.environ.copy()
        self.env = new_env
        if self.mac is None:
            self.getMac()
        if self.producer is None:
            self.getProducer()

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
            result = poller.poll(60000)
            if len(result) > 0:
                line = self.miner.stdout.readline()
                line = str(line, encoding="utf-8")
                if len(line) > 0:
                    self.get_miner_data()
    def stop(self):
        self.is_break = True
    def getProducer(self):
        client = KafkaClient(hosts="47.106.253.159:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()
    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac

    def get_miner_data(self):
        url = "http://127.0.0.1:3332/api/v1/status"
        res = requests.get(url)
        data = json.loads(res.text)
        speed = str(data['miner']['total_hashrate'])+" Bhash/s"
        program_name = "btminer-nebutech"
        coin = "Bytom"
        ret = []
        for val in data.get('miner', {}).get("devices", []):
            hash = val.get('hashrate', 0)
            id = val.get('id',0)
            info = val.get('info',0)
            res = {"id":id,"info":info,"hash":hash}
            ret.append(res)
        str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name, "coin": coin,"devices":ret}
        json_info = json.dumps(str_)
        if self.producer is None:
            self.producer = self.getProducer()
        self.producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)

def get_miner_config():
    str = """
        {"id":24774,"service_type":"eth","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"bminer","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth","WalletAddress":"bm1qyum3xzqmn0cknvs734ae7y9vjysg8nydaxxpz6","PoolAddresses":"btm.f2pool.com:9221","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddress":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/btminer-nebutech/BTMiner_NebuTech '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None

    Bin += "-url {} ".format(Primary['PoolAddress'])
    Bin += "-user {}.{} ".format(Primary['WalletAddress'],config['Worker'])
    Bin += "--api 127.0.0.1:3332 "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    return Bin + " 2>&1"

def main():
    fpath = "/opt/miner"
    ch2dir = "{}/bin".format(fpath)
    cmdline = renderCmd(ch2dir)
    if not cmdline:return
    miner = Miner()
    miner.init(cmdline)
    miner.start()
    miner.join()

if __name__ == '__main__':
    main()

