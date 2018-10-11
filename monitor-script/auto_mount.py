import subprocess

def getAllNames():
    names = []
    dirs = []
    p = subprocess.Popen("df", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = p.communicate()
    content = str(stdout, encoding='utf-8')
    contents = content.split("\n")
    for line in contents:
        tmp = line
        name = line.split(" ")[0]
        dir = tmp.split("% ")[-1]
        names.append(name)
        if "/data" in dir:
            dirs.append(dir)
    return names,dirs

def auto_mount(names,dirs):
    p = subprocess.Popen("blkid", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = p.communicate()
    content = str(stdout, encoding='utf-8')
    contents = content.split("\n")
    for line in contents:
        if 'TYPE="ext4"' in line and ' UUID="' in line:
            name = line.split(":")[0]
            if name in names:
                print(name+" is mounted!")
            else:
                for i in range(100):
                    if "/data"+str(i) not in dirs:
                        p1 = subprocess.Popen("mkdir /data"+str(i), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        p1.communicate()
                        p2 = subprocess.Popen("mount "+name+" /data"+ str(i), shell=True, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT)
                        stdout,_ = p2.communicate()
                        print("mount "+name + " at /data"+str(i))
                        dirs.append("/data"+str(i))
                        break

if __name__ == '__main__':
    names,dirs = getAllNames()
    auto_mount(names,dirs)
