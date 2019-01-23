#!/usr/bin/env python
import paramiko
import sys, time, string, glob
import subprocess

COL ="""p_time,p_loss,
current-operator,current-cellid,rsrq,rsrp,session-uptime,
subscriber-number,sinr,cqi,lac,sector-id,earfcn,phy-cellid,enb-id,access-technology"""

MSG_INTERVAL=300 #Send SMS interval in sec

class logger(object):
    def __init__(self,mask="hab_*.csv", maxlines=0, header=""):
        self._line_count = 0
        self._maxlines=maxlines
        self._mask=mask
        self._file_name = self._mask.replace("*","{:04d}".format(len(glob.glob(self._mask))+1))
        self._header=header
        if len(self._header)>0:
                    with open(self._file_name, "a") as f:
                        f.write(self._header+"\n")
    def write(self,line):
        with open(self._file_name, "a") as f:
            f.write(line+"\n")
            self._line_count += 1

        if self._maxlines>0:
            if self._line_count>self._maxlines-1:
                self._line_count=0
                self._file_name = self._mask.replace("*","{:04d}".format(len(glob.glob(self._mask))+1))
                if len(self._header)>0:
                    with open(self._file_name, "a") as f:
                        f.write(self._header+"\n")

class mt(object):
    def __init__(self, target='192.168.88.1',
                    username='admin',
                    password='',
                    look_for_keys=False,
                    timeout=10
                    ):
        self.target=target
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect(target, username=username, password=password, look_for_keys=look_for_keys, timeout=timeout)
        except:
            print ("Connection error")
            sys.exit(2)
    def read_all(self):
        rec={}
        s=[]
        stdin,stdout,stderr = self._ssh.exec_command('/interface lte info lte1 once')
        lteStatus =  stdout.read()
        for line in lteStatus.splitlines()[:-1]:
            s = line.strip().split(':')
            rec[s[0]]=s[1].strip()
        return rec
    def send_sms(self,phone="",message="test"):
        cmd='tool sms send lte1 "{}" message="{}"'.format(phone,message)
        stdin,stdout,stderr = self._ssh.exec_command(cmd)

def ping(server="8.8.8.8", count=3, wait_sec=2):

    """
    :rtype: dict or None
    """

    cmd = "ping -c {} -W {} {}".format(count, wait_sec, server).split(' ')
    try:
        output = subprocess.check_output(cmd).decode().strip()
        lines = output.split("\n")
        total = lines[-2].split(',')[3].split()[1]
        loss = lines[-2].split(',')[2].split()[0]
        timing = lines[-1].split()[3].split('/')
        return {
            'p_server': server,
            'p_min': timing[0],
            'p_time': timing[1],
            'p_max': timing[2],
            'p_mdev': timing[3],
            'p_total': total,
            'p_loss': loss,
        }
    except Exception as e:
        #print(e)
        return {
            'p_server': "N/A",
            'p_min': "N/A",
            'p_time': "N/A",
            'p_max': "N/A",
            'p_mdev': "N/A",
            'p_total': "N/A",
            'p_loss': "N/A",
        }

def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        try:
            result.update(dictionary)
        except:
            pass
    return result

def main(col):
    print(col)
    m=mt(target='192.168.88.1')
    log=logger(maxlines=10,header=col)
    next_msg=time.time()+MSG_INTERVAL
    
    while True:
        r=""    
        l=merge_dicts(m.read_all(), ping(server='8.8.8.8'))
        for i in col.split(","):
            try:
                r=r+(l[i])+","
            except:
                r=r+"N/A,"
        print(r)
        log.write(r)
        if time.time()>next_msg:
            m.send_sms(message=r)
            next_msg=time.time()+MSG_INTERVAL
        time.sleep(1)
    #for k,v in l.items():
    #    print("{}: {}").format(k,v)


if __name__ == "__main__":
    try:
        main(COL.replace("\n",""))    
    except KeyboardInterrupt:
        sys.exit(0)
