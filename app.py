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

import detect

# fmpeg -i in.mp4 -pix_fmt yuv420p -c:a copy -movflags +faststart out.mp4

FPS = 5
WORK_DIR = Path('./exp_2nd_quadrant_SD')
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
        rawImage = client.simGetImage('high_res', airsim.ImageType.Scene, vehicle_name=self.name)
        png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
        print(png.shape)
        cv2.imwrite(str(WORK_DIR/'a.png'), png)
        Ctrl.Wait(1.0)
        while stop is False:
            heap = heap[-9:] # size 10 buffer
            rawImage = client.simGetImage('high_res', airsim.ImageType.Scene, vehicle_name=self.name)
            # png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
            t = Ctrl.GetSimTime()
            msg = MsgImg(rawImage, t)
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
    def pathfollower(self):
        # ffmpeg -r 5 -i exp_small/img%d.png -vcodec libx264 -crf 15  -pix_fmt yuv420p exp_small/test.mp4
        # SD: 720x576 size 721637
        # HD: 1920x1080 size 3377913
        client = airsim.MultirotorClient()
        client.enableApiControl(True, vehicle_name=self.name)
        client.armDisarm(True, vehicle_name=self.name)
        # self.recThread.start()
        client.takeoffAsync(vehicle_name=self.name).join()
        with open(WORK_DIR/'path.csv') as f:
            rows = csv.reader(f)
            headers = next(rows)
            for i, row in enumerate(rows):
                ty = row[0]
                if ty == 'pos':
                    x, y, z, vel = [float(item) for item in row[1:]]
                    print(f'{self.name} goes to {x},{y}, {z}')
                    client.moveToPositionAsync(x, y, z, vel, vehicle_name=self.name).join()
                    print(f'{self.name} arrives at {x},{y}, {z}')
                elif ty == 'yaw':
                    yaw = float(row[1])
                    client.rotateToYawAsync(yaw).join()
                else:
                    raise ValueError(f'Unrecongnized op {ty}')
        client.landAsync().join()
        with self.mutex:
            self.stop = True
        # self.recThread.join()
        Ctrl.SetEndTime(Ctrl.GetSimTime() + 3.0) # end of simulation
    def windEffect(self):
        '''
            {
	"SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
	"SettingsVersion": 1.2,
	"SimMode": "Multirotor",
	"ClockSpeed": 1,
	"CameraDefaults": {
		"CaptureSettings": [
			{
				"ImageType": 0
			}
		]
	},
	"Vehicles": {
		"A": {
			"VehicleType": "SimpleFlight",
			"X": 0,
			"Y": 0,
			"Z": 0,
			"EnableTrace": true,
			"Cameras" : {
				"high_res": {
					"CaptureSettings" : [
						{
							"ImageType" : 0,
							"Width" : 720,
							"Height" : 576
						}
					],
					"X": 0.50, "Y": 0.00, "Z": 0.00,
					"Pitch": 0.0, "Roll": 0.0, "Yaw": 0.0
				}
			}
		},
		"B": {
			"VehicleType": "SimpleFlight",
			"X": 0,
			"Y": -3,
			"Z": 0,
			"EnableTrace": true,
			"Cameras" : {
				"high_res": {
					"CaptureSettings" : [
						{
							"ImageType" : 0,
							"Width" : 720,
							"Height" : 576
						}
					],
					"X": 0.50, "Y": 0.00, "Z": 0.00,
					"Pitch": 0.0, "Roll": 0.0, "Yaw": 0.0
				}
			}
		}
	},
	"updateGranularity": 0.01,
	"segmentSize": 1448,
	"numOfCong": 0,
	"congRate": 1.0,
	"congArea": [
		0,
		0,
		10
	],
	"initEnbApPos": [
		[
			0,
			0,
			0
		]
	],
	"nRbs": 6,
	"TcpSndBufSize": 102400,
	"TcpRcvBufSize": 102400,
	"CqiTimerThreshold": 10,
	"LteTxPower": 0,
	"p2pDataRate": "10Gb/s",
	"p2pMtu": 1500,
	"p2pDelay": 1e-3,
	"useWifi": 0,
	"isMainLogEnabled": 1,
	"isGcsLogEnabled": 0,
	"isUavLogEnabled": 0,
	"isCongLogEnabled": 0,
	"isSyncLogEnabled": 0
}
        '''
        # Ctrl.Wait(5.0)
        if self.name == 'A':
            client = airsim.MultirotorClient()
            client.enableApiControl(True, vehicle_name=self.name)
            client.armDisarm(True, vehicle_name=self.name)
            client.simSetTraceLine([1,0,1], thickness=3.0)
            client.takeoffAsync(vehicle_name=self.name).join()
            client.moveToPositionAsync(20, 0, -3, 7, vehicle_name=self.name).join()
            client.hoverAsync().join()
            client.simSetTraceLine([1,1,0], thickness=3.0)
            client.moveToPositionAsync(0, 0, -0.5, 7, vehicle_name=self.name).join()
            client.hoverAsync().join()
            client.landAsync(vehicle_name=self.name).join()
            res = -1
            msg = MsgRaw(b'bye')
            while res < 0:
                res = self.Tx(msg)
                Ctrl.Wait(0.5)
            print(f'{self.name} finished')
        elif self.name == 'B':
            Ctrl.Wait(1.0)
            res = self.Rx()
            while Ctrl.ShouldContinue() and res is None:
                res = self.Rx()
                Ctrl.Wait(0.5)
            print(f'{self.name} recv GO')
            client = airsim.MultirotorClient()
            client.enableApiControl(True, vehicle_name=self.name)
            client.armDisarm(True, vehicle_name=self.name)
            client.simSetTraceLine([1,0,1], thickness=3.0)
            client.takeoffAsync(vehicle_name=self.name).join()
            client.moveToPositionAsync(20, -3, -3, 7, vehicle_name=self.name).join()
            client.simSetTraceLine([1,1,0], thickness=3.0)
            client.moveToPositionAsync(0, -3, -0.5, 7, vehicle_name=self.name).join()
            client.hoverAsync().join()
            client.landAsync(vehicle_name=self.name).join()
            Ctrl.SetEndTime(Ctrl.GetSimTime() + 1.0)
    def customfn(self, *args, **kwargs):
        # self.pathfollower()
        # self.staticThroughputTest(0, 0.01)
        self.windEffect()
        pass
    def run(self, *args, **kwargs):
        self.beforeRun()
        self.customfn(*args, **kwargs)
        self.afterRun()
        print(f'{self.name} joined')
        
class GcsApp(GcsAppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # any self.attribute that you need
    def pathfollower(self):
        print('***********************')
        print(f'Current Working dir {WORK_DIR}')
        print('***********************')
        opt = detect.loadDefaultOpt()
        model = detect.loadModel(opt)
        
        count = 0
        lastImg = MsgImg(np.zeros((576, 720, 3), dtype=np.uint8))
        thisImg = MsgImg(np.zeros((576, 720, 3), dtype=np.uint8))
        
        lastTimestamp = 0
        T = 1/FPS
        while Ctrl.ShouldContinue():
            reply = self.Rx()
            # print(reply)
            if reply is not None:
                name, reply = reply
                if isinstance(reply, MsgRaw): # possibly a goodbye message
                    print(f'{self.name} recv {reply.data}')
                else:
                    thisImg = reply
                    thisImg.png = cv2.imdecode(airsim.string_to_uint8_array(thisImg.png), cv2.IMREAD_UNCHANGED)
                    thisImg.png = cv2.cvtColor(thisImg.png, cv2.COLOR_BGRA2BGR)
                    print(f'GCS {thisImg.png.shape}')
                    thisImg.png, allboxes = detect.detectYolo(model, thisImg.png, opt)
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
    def windEffect(self):
        client = airsim.MultirotorClient()
        client.simSetWind(airsim.Vector3r(0,0,0))
        Ctrl.Wait(1.0)
        rep = self.Rx()
        while Ctrl.ShouldContinue() and rep is None:
            rep = self.Rx()
            Ctrl.Wait(0.5)
        print(f'{self.name} set wind!')
        name, rep = rep
        y = 15
        res = self.Tx(rep, 'B')
        while res < 0:
            res = self.Tx(rep, 'B')
            Ctrl.Wait(0.5)
        print(f'{self.name} notifies B')
        while Ctrl.ShouldContinue():
            w = airsim.Vector3r(0, y, 0)
            y *= -1
            client.simSetWind(w)
            Ctrl.Wait(1.0)
        client.simPause(False)
            
    def customfn(self, *args, **kwargs):
        # self.pathfollower()
        # self.staticThroughputTest()
        self.windEffect()
        pass
    def run(self, *args, **kwargs):
        self.beforeRun()
        self.customfn(*args, **kwargs)
        self.afterRun()
        print(f'{self.name} joined')

        
        
        
        
'''
"Vehicles": {
		"A": {
			"VehicleType": "SimpleFlight",
			"X": 0,
			"Y": 0,
			"Z": 0,
			"EnableTrace": true,
			"Cameras": {
				"front-center": {
					"CaptureSettings": [
						{
							"ImageType": 0,
							"width": 1920,
							"height": 1080
						}
					]
				}
			}
		}
	},
'''
