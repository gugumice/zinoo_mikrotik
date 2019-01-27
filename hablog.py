#!/usr/bin/env python
import threading
import paramiko
import serial
import sys, time, string, glob
import subprocess
import socket
import fcntl
import struct

COL ="""tim,dat,lat,lon,spd,dir,asl,siq,p_time,p_loss,
current-operator,current-cellid,rsrq,rsrp,session-uptime,
subscriber-number,sinr,cqi,lac,sector-id,earfcn,phy-cellid,enb-id,access-technology"""

MSG_INTERVAL=30 #Send SMS interval in sec

class usbgps(object):
        def __init__(self, port="/dev/ttyACM0", baudrate=9600, timeout=1):
                self._running=True
                self._gpsdata={}
                try:
                        self._ser=serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
                        self._running=True
                except Exception as exc:
                        print(exc)
			self._running=False
			#raise StopIteration
        def _read_line(self):
                data={}
		if self.running()==False:
			return(data)
		try:
	                ln=self._ser.readline()
		except Exception as exc:
			print(exc)
			self._running=False
			#raise StopIteration
		else:
	                l=ln.split(",")
        	        data['$id']=l[0]
                	if l[0]=='$GPGGA':
                        	l=ln.split(",")
                        	data['tim']=l[1].split(".")[0]
                        	data['lat']=self._to_dec(l[2]+l[3])
                        	data['lon']=self._to_dec(l[4]+l[5])
                        	data['asl']=l[9]
                        	data['siq']=l[6]
                	if l[0]=='$GPVTG':
                        	l=ln.split(",")
                        	data['spd']=l[7]+l[8]
	                if l[0]=='$GPRMC':
        	                l=ln.split(",")
                	        data['dir']=l[8]
                        	data['dat']=l[9]
                return(data)
        def _to_dec(self,coord):
		c=coord[0:-1].split(".")
		deg=int(c[0][:-2])
		min=float(c[0][-2:]+"."+c[1])/60
		return("{}{}".format(round(deg+min,5), coord[-1]))
	def running(self):
                return(self._running)

        def next(self):
                ln={}
                if self.running:
                        ln=self._read_line()
                        while ln['$id']!='$GPGLL':
                                ln.update(self._read_line())
			del ln['$id']
                return(ln)
class GpsPoller(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.session = usbgps()
		self.current_value = {}
	def get_current_value(self):
		return self.current_value
	def run(self):
		try:
			#while True:
			while self.session.running():
                		self.current_value = self.session.next()
	                	time.sleep(1) # tune this, you might not get values that quickly
		#except StopIteration:
		#	pass
		except KeyboardInterrupt:
			sys.exit(2)

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

    def send_sms(self,phone="29413099",message="test"):
        cmd='/tool sms send lte1 "{}" message="{}"'.format(phone,message)
        stdin,stdout,stderr = self._ssh.exec_command(cmd)
	time.sleep(.5)
	print("Sending to {}\n {}".format(phone,message))
	stdin,stdout,stderr = self._ssh.exec_command('/')

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

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15]))[20:24])

def main(col):

    print(col)
    m=mt(target='192.168.88.1')
    log=logger(mask='/home/pi/log/hab_*.csv',maxlines=10,header=col)

    next_msg=time.time()+MSG_INTERVAL

    gpsp = GpsPoller()
    gpsp.daemon = True
    gpsp.start()
    m.send_sms(message=get_ip_address('eth0'))
    while True:
        r="" 
        l=merge_dicts(m.read_all(), ping(server='8.8.8.8'), gpsp.get_current_value())
        for i in col.split(","):
            try:
                r=r+(l[i])+","
            except:
                r=r+"N/A,"
        print(r)
        log.write(r)
        if time.time()>next_msg:
            msg='http://maps.google.com?q={},{} asl:{} spd:{}'.format(l['lat'],l['lon'],l['asl'],l['spd'])
	    m.send_sms(message=msg)
            next_msg=time.time()+MSG_INTERVAL
        time.sleep(5)
    #for k,v in l.items():
    #    print("{}: {}").format(k,v)


if __name__ == '__main__':
	try:
        	main(COL.replace("\n",""))    
	except KeyboardInterrupt:
        	sys.exit(0)
