# -*- coding:utf-8 -*-
import json
import os
import select
import subprocess
import threading
import time
import uuid
import sys
import requests

from pykafka import KafkaClient

LOGGER_PATH = "/opt/miner/iMiner"
if LOGGER_PATH not in sys.path:
    sys.path.insert(0, LOGGER_PATH)

import logger

log = logger.create_logger(file_name='bminer.log')


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
            log.error("miner not started")
            return
        try:
            self.process()
        except Exception as e:
            log.exception(e)
            self.miner.kill()

    def process(self):
        poller = select.poll()
        poller.register(self.miner.stdout, select.POLLIN)
        while True:
            ret_code = self.miner.poll()
            if ret_code is not None:
                log.error("miner has exit: {}".format(ret_code))
                return
            if self.is_break:
                log.error("miner stoped")
                self.miner.kill()
                return
            time.sleep(6)
            self.get_miner_data()

    def get_miner_data(self):
        url = "http://127.0.0.1:1880/api/status"
        try:
            res = requests.get(url)
            res_json = json.loads(res.text)
            speed = 0
            miners = res_json["miners"]
            ret = []
            program_name = "bminer"
            for key, value in miners.items():
                id = key
                device = value["device"]
                hash = float(value["solver"]["solution_rate"]) / 1024 / 1024
                hash = float('%.3f' % hash)
                speed += hash
                temperature = device["temperature"]
                gpu_power_usage = device["power"]
                fan = device["fan_speed"]
                res = {"id": id, "info": None, "hash": hash, "fan": fan, "temperature": temperature,
                       "gpu_power_usage": gpu_power_usage}
                ret.append(res)
            speed = str(speed) + " Mhash/s"
            str_ = {"mac": self.mac, "time": time.time(), "speed": speed, "program_name": program_name,
                    "coin": self.coin,
                    "devices": ret}
            json_info = json.dumps(str_)
            if self.producer is None:
                self.getProducer()
            self.producer.produce(bytes(json_info, encoding="utf8"))
            log.info(json_info)
        except Exception as e:
            log.exception(e)

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

    def getCoin(self):
        json_conf = get_miner_config()
        self.coin = json_conf["Primary"]["CoinName"]


def get_miner_config():
    str = """
            {"id":24774,"service_type":"eth","status":0,"on":true,
            "config":{"Version":3,"Overclock":1,"Program":"bminer",
            "Algorithm":"ethash","Extra":"","IsManualPool":0,
            "Primary":{"CoinName":"eth","WalletAddress":"0x128519eba3C0495C304D1b048693Bd10a5207A60",
            "PoolAddress":"moseth.uupool.cn:5582","PoolName":"uupool.cn","Algorithm":"",
            "IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},
            "Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,
            "PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"",
            "CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92",
            "App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,
            "frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,
            "GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0",
            "GPUTargetFanSpeed":90}]}}
    """
    json_conf = json.loads(PARAM)
    json_conf["config"]["Worker"] = "jianhuaixie"
    return json_conf["config"]


def renderCmd(pwd):
    config = get_miner_config()
    Bin = '{}/bminer/bminer '.format(pwd)
    Primary = config['Primary']

    if len(Primary['WalletAddress']) == 0:
        log.error('none WalletAddress')
        return None
    algotithms = dict(
        btm='tensority://',
        ethash='ethproxy://',
        equihash='stratum://',
    )

    eth_protocols = {
        'ethproxy://': 'f2pool.com|dwarfpool.com|sparkpool.com|waterhole.xyz|viabtc.com|uupool.cn',
        'ethash://': 'nanopool.org|ethermine.org',
        'ethstratum://': 'coinfoundry.org|coinotron.com|miningpoolhub.com',
    }

    protocol = algotithms.get(config['Algorithm'], "")
    if config['Algorithm'] == 'ethash':
        for k, v in eth_protocols.items():
            for j in v.split('|'):
                if Primary['WalletAddress'].find(j) >= 0:
                    protocol = k
                    break

    Bin += "-uri {}".format(protocol)
    Bin += "{}.{}".format(Primary['WalletAddress'], config['Worker'])
    Bin += "@{} ".format(Primary['PoolAddress'])
    Bin += "-api 127.0.0.1:1880 "

    if len(config['Extra']) > 0:
        Bin += config['Extra']
    Bin += " 2>&1"
    return Bin


def main():
    fpath = "/opt/miner"
    ch2dir = "{}/bin".format(fpath)
    cmdline = renderCmd(ch2dir)

    if not cmdline:
        log.error("Can't render command")
        return

    log.info("command: {0}".format(cmdline))

    miner = Miner()
    miner.init(cmdline)
    miner.start()
    miner.join()


if __name__ == '__main__':
    log.info("=" * 60 + "start bminer mine program" + "=" * 60)

    if len(sys.argv) < 2:
        log.error("usage: python3 bminer.py mine_parameter_json_str")
    else:
        PARAM = sys.argv[1]
        main()
