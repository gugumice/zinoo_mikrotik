#!/usr/bin/env python
import sys, time, serial
import subprocess
import threading
import paramiko

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

    def _read_line(self):
        data={}
        if self.running()==False:
			return(data)
        try:
            ln=self._ser.readline()
        except Exception as exc:
            print(exc)
            self._running=False
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

class ping_srv(object):
    def __init__(self,server='8.8.8.8',count=3, wait_sec=2):
        self._running=True
        self.ping_ok=False
        self._server=server
        self._count=count
        self._wait_sec=wait_sec
    def running(self):
        return(self._running)
    def next(self):
        try: 
            cmd = "ping -c {} -W {} {}".format(self._count, self._wait_sec, self._server).split(' ')
            output = subprocess.check_output(cmd).decode().strip()
        except Exception as e:
            #print(e)
            self.ping_ok=False
            return {
                'p_status': self.ping_ok,
                'p_server': self._server,
                'p_min': 'NaN',
                'p_time': 'NaN',
                'p_max': 'NaN',
                'p_mdev': 'NaN',
                'p_total': 'NaN',
                'p_loss': 'NaN',
            }
        else:
            self.ping_ok=True
            lines = output.split("\n")
            total = lines[-2].split(',')[3].split()[1]
            loss = lines[-2].split(',')[2].split()[0]
            timing = lines[-1].split()[3].split('/')
            return{
                'p_status': self.ping_ok,
                'p_server': self._server,
                'p_min': timing[0],
                'p_time': timing[1],
                'p_max': timing[2],
                'p_mdev': timing[3],
                'p_total': total,
                'p_loss': loss,
                }

class mt(object):
    """
    Connects to Microtik, retuns response to command
    If no connection - try to establish
    """
    def __init__(self, target='192.168.78.1',
                    username='admin',
                    password='',
                    look_for_keys=False,
                    timeout=5
                    ):
        self.target=target
        self._ssh = None
        self._username=username
        self._password=password
        self._look_for_keys=look_for_keys
        self._timeout=timeout
        self._running=True
    def _connect(self):
        try:
            print("Connecting {}".format(self.target))
            self._ssh = None
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh.connect(self.target, username=self._username, password=self._password, look_for_keys=self._look_for_keys, timeout=self._timeout)
            self._running=True
        except Exception as e:
            print("Cannot establish connection to {} - {}".format(self.target,e))
            self._running=False
    def running(self):
        return(self._running)
    def next(self):
        rec={}
        s=[]
        #If no connect - try
        if not self.running():
            self._connect()
        #Still no connect - return empty dict
        if not self.running:
            return(rec)
        try:
            stdin,stdout,stderr = self._ssh.exec_command('/interface lte info lte1 once',timeout=self._timeout)
        except Exception as e:
            print("Lost connection to {} - {}".format(self.target,e))
            self._connect()
            return(rec)
        else:
            lteStatus =  stdout.read()
            for line in lteStatus.splitlines()[:-1]:
                s = line.strip().split(':')
                rec[s[0]]=s[1].strip()
            return rec

    def send_sms(self, phone="29413099", message="test"):
        time.sleep(.1)
        cmd='/tool sms send lte1 "{}" message="{}"'.format(phone,message)
        print("Sending to {}\n {}".format(phone,message))
        stdin,stdout,stderr = self._ssh.exec_command(cmd)
        stdin,stdout,stderr = self._ssh.exec_command('/')
        time.sleep(.2)

class poller(threading.Thread):
    def __init__(self, obj, refresh=1):
        threading.Thread.__init__(self)
        self.session=obj
        self._current_value={}
        self._refresh=refresh
    def get_current_value(self):
        return(self._current_value)
    def run(self):
        while self.session.running():
            self._current_value=self.session.next()
            #print(self._current_value)
            time.sleep(self._refresh)

def main():
    mt_data=mt()
    png_data=poller(ping_srv(),refresh=5)
    png_data.daemon=True
    png_data.start()
    gps_data=poller(usbgps(),refresh=1)
    gps_data.daemon=True
    gps_data.start()
    
    while True:
        print(png_data.get_current_value(),gps_data.get_current_value(),mt_data.next())
        #print(gps_data.get_current_value())
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()    
    except KeyboardInterrupt:
        sys.exit(0)
