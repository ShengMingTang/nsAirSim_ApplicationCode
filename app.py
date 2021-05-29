from appBase import *
'''
Custom App code
'''
import threading
import heapq
from pathlib import Path
import setup_path
import airsim
import cv2
from msg import *
from ctrl import *
FPS = 10
OUT_DIR = Path('./output')
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
        while stop is False:
            if len(heap) >= maxSize:
                heapq.heappop(heap)
            rawImage = client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
            png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
            t = Ctrl.GetSimTime()
            msg = MsgImg(png, t)
            heapq.heappush(heap, (t, msg))
            ress = self.Tx([item[1] for item in heap]) # transmit as much as it can
            print(f'{self.name} ress = {ress}')
            for res in ress:
                if res >= 0:
                    heapq.heappop(heap)
                else:
                    break
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
        client.takeoffAsync(vehicle_name=self.name).join()
        self.recThread.start()
        endTime = Ctrl.GetSimTime() + 10 # 10 seconds video
        while Ctrl.GetSimTime() < endTime:
            client.moveByVelocityBodyFrameAsync(2, 0, 0, duration=1.0).join()
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
        lastImg = None
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
                    lastImg = reply.png
                print(f'{self.name} recv msg')
            if lastImg is not None:
                cv2.imwrite(str(OUT_DIR/('img%05d.png'%(count))), lastImg)
                count += 1
            Ctrl.Wait(1/FPS)

    def run(self, *args, **kwargs):
        self.beforeRun()
        self.customfn(*args, **kwargs)
        self.afterRun()
        print(f'{self.name} joined')