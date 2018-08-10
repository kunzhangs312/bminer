# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import re
import subprocess
import select
import time
import sys
import uuid
import json

class my_miner:
    miner = None
    turn_off = False
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    mac = None
    producer = None
    def start_miner(self,params):
        if self.mac is None:
            self.getMac()
        if self.producer is None:
            self.getProducer()
        cmd = './xdag-gpu ' + params + ' 2>&1'
        self.miner = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
        poller = select.poll()
        READ_ONLY = (select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR)
        poller.register(self.miner.stdout, READ_ONLY)
        while True:
            try:
                if self.turn_off:break
                events = poller.poll(60000)
                if len(events)>0:
                    line = self.miner.stdout.readline()
                    line = str(line,encoding="utf-8")
                    if len(line)>0:
                        self.parse_hash(line)
                    else:
                        self.check_status()
                        time.sleep(1)
            except Exception as e:
                print(e)

    def parse_hash(self, line):
        ansi_line = self.ansi_escape.sub('', line)
        if ansi_line.find('Speed') > 0:
            log_stats = ansi_line.split()
            speed = log_stats[-1]+" "+log_stats[-3]
            program_name = log_stats[-6].split("|")[-1]
            coin = program_name.split("-")[0]
            str = {"mac":self.mac,"time":time.time(),"speed":speed,"program_name":program_name,"coin":coin}
            json_info = json.dumps(str)
            if self.producer is None:
                self.producer = self.getProducer()
            self.producer.produce(bytes(json_info, encoding="utf8"))
            print(json_info)
    def getProducer(self):
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'miner']
        self.producer = topic.get_producer()
    def getMac(self):
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        self.mac = mac
    def check_status(self):
        ret_code = self.miner.poll()
        if ret_code is not None:
            print('miner status: ', ret_code)
            self.stop()
    def stop(self):
        self.turn_off = True
        time.sleep(1)
        self.miner.kill()

miner = my_miner()
miner.start_miner(' '.join(sys.argv[1:]))
