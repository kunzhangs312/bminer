# encoding: utf-8
# 取消挖矿超频

import subprocess
from xml.etree import ElementTree


def main():
    p = subprocess.Popen("lspci |grep VGA", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = p.communicate()
    stdout = str(stdout, encoding='utf-8')
    if "AMD" in stdout:
        print("AMD Card")
        p = subprocess.Popen("/opt/amdcovc-0.3.9.2/amdcovc -a 0-8 fanspeed=default", shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        stdout, _ = p.communicate()
    elif "NVIDIA" in stdout:
        print("NVIDIA Card")
        p = subprocess.Popen("nvidia-smi -q -x", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = p.communicate()
        xml_str = str(stdout, encoding='utf-8')
        if len(xml_str) > 100:
            page = ElementTree.fromstring(xml_str)
            if page is not None:
                gpus_number = page.getiterator("attached_gpus")
                for i in range(gpus_number):
                    Id = i
                    Level = 0
                    GPUGraphicsClockOffset = 0
                    GPUMemoryTransferRateOffset = 0
                    cmd1 = "nvidia-settings -a [gpu:" + str(Id) + "]/GPUPowerMizerMode=0 " \
                           + "-a [gpu:" + str(Id) + "]/GPUFanControlState=0 " \
                           + " -a [gpu:" + str(Id) + "]/GPUGraphicsClockOffset[" + str(Level) + "]=" + str(
                        GPUGraphicsClockOffset) \
                           + " -a [gpu:" + str(Id) + "]/GPUMemoryTransferRateOffset[" + str(Level) + "]=" + str(
                        GPUMemoryTransferRateOffset)
                    p = subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout, _ = p.communicate()
    else:
        print("None GPU Card")


if __name__ == '__main__':
    main()
