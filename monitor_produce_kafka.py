# encoding: utf-8
import time
import psutil
from pykafka import KafkaClient
import json
import requests
import re
import uuid
import socket
import platform
import subprocess
from xml.etree import ElementTree

def getDisk():
    disk_partitions = psutil.disk_partitions()
    partitions_info = []
    for partition in disk_partitions:
        fstype = partition.fstype
        if str(fstype) == "ext4":
            device = partition.device
            mountpoint = partition.mountpoint
            sdiskusage = psutil.disk_usage(mountpoint)
            total = int(sdiskusage.total/1024/1024)
            used = int(sdiskusage.used/1024/1024)
            free = int(sdiskusage.free/1024/1024)
            percent = sdiskusage.percent
            partition_info = {"device":device,"total":total,"used":used,"free":free,"percent":percent}
            partitions_info.append(partition_info)
    sdiskusage = psutil.disk_usage('/')
    total = int(sdiskusage.total/1024/1024)
    used = int(sdiskusage.used / 1024 / 1024)
    free = int(sdiskusage.free/1024/1024)
    percent = sdiskusage.percent
    partition_info = {"device": '/', "total": total, "used": used, "free": free, "percent": percent}
    partitions_info.append(partition_info)
    return partitions_info

def getCPU():
    return psutil.cpu_percent()

def getCPUType():
    cpu_type = None
    with open('/proc/cpuinfo') as f:
        for line in f:
            if 'model name' in line:
                cpu_type = line.split(": ")[-1]
                break
    return cpu_type

def getCores():
    return psutil.cpu_count()

def getMem():
    svmen = psutil.virtual_memory()  # total percent used free active inactive buffers cached shared slab
    total = "%.2f" % (svmen.total/1024/1024)
    percent = svmen.percent
    used = "%.2f" % (svmen.used/1024/1024)
    free = "%.2f" % (svmen.free / 1024 / 1024)
    active = "%.2f" % (svmen.active / 1024 / 1024)
    inactive = "%.2f" % (svmen.inactive / 1024 / 1024)
    buffers = "%.2f" % (svmen.buffers / 1024 / 1024)
    cached = "%.2f" % (svmen.cached / 1024 / 1024)
    shared = "%.2f" % (svmen.shared / 1024 / 1024)
    return {"total":total,"percent":percent,"used":used,"free":free,"active":active,"inactive":inactive,"buffers":buffers,"cached":cached,"shared":shared}

def getNet():
    def get_keys():
        key_info = psutil.net_io_counters(pernic=True).keys()
        recv = {}
        sent = {}
        for key in key_info:
            recv.setdefault(key,psutil.net_io_counters(pernic=True).get(key).bytes_recv)
            sent.setdefault(key, psutil.net_io_counters(pernic=True).get(key).bytes_sent)
        return key_info, recv, sent
    def get_rate(func):
        key_info, old_recv, old_sent = func()
        time.sleep(1)
        key_info, now_recv, now_sent = func()
        net_in = {}
        net_out = {}
        for key in key_info:
            net_in.setdefault(key, (now_recv.get(key) - old_recv.get(key)) / 1024/1024)
            net_out.setdefault(key, (now_sent.get(key) - old_sent.get(key)) / 1024/1024)
        return key_info, net_in, net_out
    return get_rate(get_keys)

def getMac():
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return mac

def get_out_ip():
    text = requests.get("http://txt.go.sohu.com/ip/soip").text
    ip = re.findall(r'\d+.\d+.\d+.\d+', text)
    return ip

def getIP():
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except socket.error:
        return "127.0.0.1"


def GetCPUorDiskTemper(type='Core'):
    dict_cpu_temp = {}
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
    else:
        temps = {}
    cpu_each = []
    names = list(temps.keys())
    for name in names:
        if name in temps:
            for entry in temps[name]:
                if type in entry.label:
                    dict_cpu_temp[entry.label] = entry.current
                    cpu_each.append(dict_cpu_temp[entry.label])
    if len(dict_cpu_temp) > 0:
        cpu_top = sorted(dict_cpu_temp.items(),key=lambda d:d[0])[0][1]
    else:
        cpu_top = None
    return {"cpu_top":cpu_top,"cpu_each":cpu_each}

def getSystemVersion():
    return platform.platform()

def getBoottime():
    return psutil.boot_time()

def main():
    mac = getMac()
    ip = getIP()
    platform = getSystemVersion()
    out_ip = get_out_ip()
    in_ = 0
    out_ = 0
    key_info, net_in, net_out = getNet()
    for key in key_info:
        in_ += net_in.get(key)
        out_ += net_out.get(key)
    in_ = "%.2f" % in_
    out_ = "%.2f" % out_
    mem = getMem()  # {'inactive': '441.24', 'percent': 94.1, 'total': '1743.71', 'free': '81.80', 'cached': '162.67', 'buffers': '20.31', 'active': '1072.55', 'used': '1478.93', 'shared': '15.42'}
    cores = getCores()
    cpuUsage = getCPU()
    disks = getDisk()  # [{'device': '/dev/sda1', 'free': 21241, 'used': 14969, 'total': 38172, 'percent': 41.3}]
    cpu_t = GetCPUorDiskTemper()["cpu_top"]
    cpu_type = getCPUType()
    boot_time = getBoottime()
    gpu_infos = get_gpu_infos()
    info = {"mac": mac,"platform":platform, "ip": ip,"out_ip":out_ip, "in_flow": in_, "out_flow": out_, "cores": cores, "cpu_usage": cpuUsage,
            "cpu_temperature": cpu_t,"cpu_type":cpu_type, "disks": disks, "memory": mem, "time": time.time(),"boot_time":boot_time,"gpu_infos":gpu_infos}
    json_info = json.dumps(info)
    return json_info


def get_gpu_infos():
    p = subprocess.Popen("nvidia-smi -q -x",shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout,_ = p.communicate()
    xml_str = str(stdout,encoding='utf-8')
    gpu_infos = []
    if len(xml_str)>100:
        page = ElementTree.fromstring(xml_str)
        if page is not None:
            gpus = page.getiterator("gpu")
            for gpu in gpus:
                product_name = gpu.find("product_name").text
                fb_memory_usage = gpu.find("fb_memory_usage")
                total = fb_memory_usage.find("total").text
                used = fb_memory_usage.find("used").text
                free = fb_memory_usage.find("free").text
                gpu_temperature = gpu.find("temperature").find("gpu_temp").text
                gpu_power = gpu.find("power_readings").find("power_draw").text
                power_limit = gpu.find("power_readings").find("power_limit").text
                gpu_info = {"product_name":product_name,"total":total,"used":used,"free":free,"gpu_temperature":gpu_temperature,"gpu_power":gpu_power,"power_limit":power_limit}
                gpu_infos.append(gpu_info)
    return gpu_infos

if __name__ == '__main__':
    client = KafkaClient(hosts="192.168.0.69:9092")
    topic = client.topics[b'monitor']
    producer = topic.get_producer()
    while True:
        json_info = main()
        producer.produce(bytes(json_info, encoding = "utf8"))
        print(json_info)
        time.sleep(60)