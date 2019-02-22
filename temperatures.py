
#!/usr/bin/env python
import sys, time, glob
class ds(object):
        """
        Reads sensors from path
        Returns temperature readings in Celsius
        """
        def __init__(self,path='/sys/bus/w1/devices/??-*'):
                self._running=True
                self._sensors=glob.glob(path+'/w1_slave')
                if len(self._sensors)==0:
                        self._running=False
        def __str__(self):
                return(str(self.run())[1:-1].replace("'",""))
        def __repr__(self):
                return{self.run}
        def runing(self):
                return(self._running)
        def _read_sensor(self,sensor):
                s=sensor[20:-9]
                try:
                        f = open(sensor, 'r')
                except IOError:
                        return{s: 'NaN'}
                else:
                        lines=f.readlines()
                        f.close()
                        if lines[0].strip()[-3:] != 'YES':
                                return{s: 'Err'}
                        else:
                                return{s: round(float(lines[1].strip()[lines[1].                                               find('t=')+2:])/1000,1)}
        def run(self):
                readout={}
                for sensor in self._sensors:
                        readout.update(self._read_sensor(sensor))
                return(readout)
def main():
        while True:
                d=ds()
                #print(d.run())
                print(d)
                #print(d.runing())
                time.sleep(1)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
