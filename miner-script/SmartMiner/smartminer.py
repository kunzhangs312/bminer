# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import uuid
import subprocess
import os
import re
import select
import time
import json
import threading

class Miner(threading.Thread):
    miner = None
    cmd = None
    is_break = False
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    mac = None
    producer = None
    coin = None
    def init(self,cmd):
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
            try:
                events = poller.poll(60000)
                if len(events)>0:
                    line = self.miner.stdout.readline()
                    line = str(line,encoding="utf-8")
                    if len(line) > 0:
                        self.parse_hash(line)
                else:
                    self.check_status()
            except Exception as e:
                print(e)

    def parse_hash(self,line):
        ansi_line = self.ansi_escape.sub('', line)
        if ansi_line.find('Sols/s') > 0:
            hash = ansi_line.split()[4]
            speed = hash +" Sols/s"
            coin = "aion"
            program_name = "smartminer"
            str = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name, "coin": coin}
            json_info = json.dumps(str)
            if self.producer is None:
                self.producer = self.getProducer()
            self.producer.produce(bytes(json_info, encoding="utf8"))
            print(json_info)

    def check_status(self):
        ret_code = self.miner.poll()
        if ret_code is not None:
            print('miner status: ', ret_code)
            self.stop()
    def getProducer(self):
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()
    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac
    def stop(self):
        self.turn_off = True
        time.sleep(1)
        self.miner.kill()
        os.system("pgrep SmartMiner | xargs kill -9")
    def getCoin(self):
        json_conf = get_miner_config()
        self.coin = json_conf["Primary"]["CoinName"]

def get_miner_config():
    str = """
        {"id":24774,"service_type":"AION","status":0,"on":true,"config":{"GpuNum":1,"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"aion","WalletAddress":"0xa0c238f3b427320e5231e8703335fe52620895b08ded92fcd05f9775698bc321","PoolAddress":"aion.f2pool.com:6677","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(str)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]

def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/SmartMiner/SmartMiner '.format(pwd)
    Primary = config['Primary']
    if len(Primary['WalletAddress']) == 0:
        print('none WalletAddress')
        return None

    Bin += "-l {} ".format(Primary['PoolAddress'])
    Bin += "-u {}.{} ".format(Primary['WalletAddress'], config['Worker'])

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    else:
        devs = ' '.join([str(i) for i in range(config['GpuNum'])])
        Bin += "-cd {}".format(devs)
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










