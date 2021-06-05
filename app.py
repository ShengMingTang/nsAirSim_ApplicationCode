import setup_path
import airsim
from appBase import *
from msg import *
from ctrl import *
'''
Custom App code
'''
import threading
import heapq
from pathlib import Path
import cv2
import csv

# ffmpeg -r 5 -i exp_small/img%d.png -vcodec libx264 -crf 15  -pix_fmt yuv420p exp_small/test.mp4
FPS = 5
WORK_DIR = Path('./exp_small')
class UavApp(UavAppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mutex = threading.Lock()
        self.stop = False
        self.recThread = threading.Thread(target=UavApp.recorder, args=(self,1/FPS, 256))
    def recorder(self, period, maxSize):
        heap = []
        stop = False
        client = airsim.MultirotorClient()
        rawImage = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
        png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
        print(png.shape)
        Ctrl.Wait(1.0)
        while stop is False:
            heap = heap[-9:] # size 10 buffer
            rawImage = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
            png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
            t = Ctrl.GetSimTime()
            msg = MsgImg(png, t)
            heap.append(msg)
            ress = self.Tx(heap) # transmit as much as it can
            head = 0
            print(ress)
            for res in ress:
                if res >= 0:
                    head += 1
                else:
                    break
            heap = heap[head:]
            Ctrl.Wait(period)
            with self.mutex:
                stop = self.stop
        msg = MsgRaw(b'bye')
        res = self.Tx(msg)
        while res < 0:
            res = self.Tx(msg)
        print(f'{self.name} says bye')
            
    def customfn(self, *args, **kwargs):
        client = airsim.MultirotorClient()
        client.enableApiControl(True, vehicle_name=self.name)
        client.armDisarm(True, vehicle_name=self.name)
        self.recThread.start()
        client.takeoffAsync(vehicle_name=self.name).join()
        with open(WORK_DIR/'path.csv') as f:
            rows = csv.reader(f)
            headers = next(rows)
            for i, row in enumerate(rows):
                t = row[0]
                x, y, z, vel = [float(item) for item in row[1:]]
                if t == 'pos':
                    client.moveToPositionAsync(x, y, z, vel).join()
                    print(f'{self.name} goes to {x},{y}, {z}')
                else:
                    raise ValueError(f'Unrecongnized op {t}')
        with self.mutex:
            self.stop = True
        self.recThread.join()
        
    def run(self, *args, **kwargs):
        self.beforeRun()
        self.customfn(*args, **kwargs)
        self.afterRun()
        print(f'{self.name} joined')
        
class GcsApp(GcsAppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # any self.attribute that you need
        
    def customfn(self, *args, **kwargs):
        count = 0
        lastImg = MsgImg(np.zeros((144, 256, 3), dtype=np.uint8))
        thisImg = MsgImg(np.zeros((144, 256, 3), dtype=np.uint8))
        
        lastTimestamp = 0
        T = 1/FPS
        while True:
            reply = self.Rx()
            # print(reply)
            if reply is not None:
                name, reply = reply
                if isinstance(reply, MsgRaw): # possibly a goodbye message
                    print(f'{self.name} recv {reply.data}')
                    Ctrl.SetEndTime(Ctrl.GetSimTime() + 1.0) # end of simulation
                    break
                else:
                    thisImg = reply
                    lastTimestamp = thisImg.timestamp - T/2
                print(f'{self.name} recv msg')
            
            #  t_last t-T/2| ... (thisImg) | t+T/2
            while thisImg.timestamp > lastTimestamp + T/2: # too late, patch
                if lastImg.timestamp != 0:
                    cv2.imwrite(str(WORK_DIR/('img%d.png'%(count))), lastImg.png)
                    count += 1
                    print(f'patched {count}')
                lastTimestamp += T
            if thisImg.timestamp != lastImg.timestamp:
                cv2.imwrite(str(WORK_DIR/('img%d.png'%(count))), thisImg.png)
                count += 1
                lastImg = thisImg
                print(f'GCS count={count}')
            Ctrl.Wait(T)

    def run(self, *args, **kwargs):
        self.beforeRun()
        self.customfn(*args, **kwargs)
        self.afterRun()
        print(f'{self.name} joined')