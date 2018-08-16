# encoding: utf-8
import subprocess
import json
import sys

def main():
    params_str = """
            {"id":24774,"service_type":"Zcash","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"ewbf-miner","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth","WalletAddress":"t1emzuNbemjqnEhEue74NL3BxsR4cA1ajfP","PoolAddress":"zec-eu1.nanopool.org:6666","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":118,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":77}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
        """
    params_str = sys.argv[1]
    p = subprocess.Popen("lspci |grep VGA", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = p.communicate()
    stdout = str(stdout, encoding='utf-8')
    if "AMD" in stdout:
        print("AMD Card")
        str_json = json.loads(params_str)
        if str_json["overclock_info"] is not None:
            overclock_info = str_json["overclock_info"]
            cpu = overclock_info['cpu']
            frequency = cpu['frequency']
            cmd = "echo 'performance' >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd = "echo " + str(frequency) + " >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd = "echo 'powersave' >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, _ = p.communicate()
            fans = overclock_info['fan']
            for fan in fans:
                Id = fan["Id"]
                GPUTargetFanSpeed = fan['GPUTargetFanSpeed']
                p = subprocess.Popen("/opt/amdcovc-0.3.9.2/amdcovc fanspeed:"+str(Id)+"="+GPUTargetFanSpeed, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout, _ = p.communicate()
    elif "NVIDIA" in stdout:
        print("NVIDIA Card")
        str_json = json.loads(params_str)
        if str_json["overclock_info"] is not None:
            overclock_info = str_json["overclock_info"]
            cpu = overclock_info['cpu']
            frequency = cpu['frequency']
            cmd = "echo 'performance' >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd = "echo "+str(frequency)+" >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cmd = "echo 'powersave' >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, _ = p.communicate()
            gpus = overclock_info['gpu']
            for gpu in gpus:
                Id = gpu["Id"]
                Level = gpu['Level']
                PowerLimit = gpu['PowerLimit']  # 最大功率
                GPUGraphicsClockOffset = gpu['GPUGraphicsClockOffset']  # GPU频率
                GPUMemoryTransferRateOffset = gpu['GPUMemoryTransferRateOffset']  # 现存频率
                GPUTargetFanSpeed = gpu['GPUTargetFanSpeed']  # 风扇转速
                cmd0 = "nvidia-smi -i " + str(Id) +" -pl "+str(PowerLimit)
                cmd1 = "nvidia-settings -a [gpu:"+str(Id)+"]/GPUPowerMizerMode=1 " \
                       + "-a [gpu:"+str(Id)+"]/GPUFanControlState=1 " \
                       + "-a [fan:"+str(Id)+"]/GPUTargetFanSpeed="+str(GPUTargetFanSpeed) \
                       +" -a [gpu:"+str(Id)+"]/GPUGraphicsClockOffset["+str(Level)+"]="+str(GPUGraphicsClockOffset) \
                       + " -a [gpu:"+str(Id)+"]/GPUMemoryTransferRateOffset["+str(Level)+"]="+str(GPUMemoryTransferRateOffset)
                p = subprocess.Popen(cmd0, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                p = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout, _ = p.communicate()
    else:
        print("None GPU Card")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("please input the params name")
    else:
        main()