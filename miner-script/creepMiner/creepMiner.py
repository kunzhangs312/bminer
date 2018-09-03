# -*- coding:utf-8 -*-
import json
import subprocess

def main():
    params = """{"miningInfo":"http://pool.creepminer.net:8124","submission":"http://pool.creepminer.net:8124","wallet":"BURST-SQW7-7YNR-ZVAE-65HXA","plots":[{"path":"/data","type":"sequential"}],"processorType":"OPENCL"}"""
    params_json = json.loads(params)
    with open('/root/.creepMiner/1.7.19/mining.conf') as json_file:
        data = json.load(json_file)
        data['mining']['processorType'] = params_json['processorType']
        data['mining']['urls']['miningInfo'] = params_json['miningInfo']
        data['mining']['urls']['submission'] = params_json['submission']
        data['mining']['urls']['wallet'] = params_json['wallet']
        data['mining']['plots'] = params_json['plots']
        json_file.close()
        fb = open('/root/.creepMiner/1.7.19/mining.conf','w')
        fb.write(json.dumps(data))
        fb.close()
    cmd = None
    if params_json['processorType'] == "CPU":
        cmd = "/opt/miner/creepMiner-1.7.19.0/run.sh"
    else:
        cmd = "/opt/miner/creepMiner-opencl-1.7.19.0/run.sh"
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

if __name__ == '__main__':
    main()