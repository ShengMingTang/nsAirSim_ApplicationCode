import setup_path
import airsim
import zmq
import threading
import re
import time
import csv
from pathlib import Path
from functools import partial
# custom import
from ctrl import Ctrl

class Uav(threading.Thread):
    def __init__(self, name, zmqSendPort, zmqRecvPort, context, **kwargs):
        threading.Thread.__init__(self)
        # socket need to be handled outside of this scope
        self.name = name
        self.zmqSendSocket = context.socket(zmq.REQ)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqSendSocket.setsockopt(zmq.RCVTIMEO, 1000)

        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True, vehicle_name=self.name)
        self.client.armDisarm(True, vehicle_name=self.name)
        
        self.kwargs = kwargs
    def Tx(self, payload, flags=zmq.NOBLOCK):
        try:
            self.zmqSendSocket.send(payload, flags=flags)
            res = self.zmqSendSocket.recv()
            res = int.from_bytes(res, 'little', signed=True)
            return res
        except zmq.ZMQError:
            return -1
    def Rx(self, flags=zmq.NOBLOCK):
        try:
            return self.zmqRecvSocket.recv(flags)
        except zmq.Again:
            return None
    def selfTest(self):
        while Ctrl.GetSimTime() < 1.0:
            time.sleep(0.1)
        self.Tx(b'I\'m %b' % (bytes(self.name, encoding='utf-8')))
        s = self.Rx()
        while s == None:
            time.sleep(0.1)
            s = self.Rx()
        print(f'{self.name} recv: {s}')
    def throughputVsDistTest(self, filename, period=0.01, stay=1.0, step=50):
        with open(filename, 'w', newline='') as f:
            wrt = csv.writer(f)
            wrt.writerow(['Time', 'X', 'ByteCount'])
            pose = self.client.simGetVehiclePose(vehicle_name=self.name)
            pose.position.x_val = 0
            lastTx = Ctrl.GetSimTime()
            lastMv = lastTx
            response = self.client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
            lastRes = 0
            while Ctrl.ShouldContinue():
                if lastRes > 0:
                    lastRes = self.Tx(bytes(response))
                    self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
                    continue
                t = Ctrl.GetSimTime()
                if t - lastMv > stay:
                    pose.position.x_val += step
                    self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
                    lastMv = t
                if t - lastTx > period:
                    res = self.Tx(bytes(response))
                    if res >= 0:
                        wrt.writerow([t, pose.position.x_val, len(bytes(response)), res])
    def staticThroughputTest(self,dist, period=0.01):
        total = 0
        pose = self.client.simGetVehiclePose(vehicle_name=self.name)
        pose.position.x_val = dist
        lastTx = Ctrl.GetSimTime()
        # response = self.client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
        trans = bytes(50*1024)
        self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
        while Ctrl.ShouldContinue():
            t = Ctrl.GetSimTime()
            if t - lastTx > period:
                res = self.Tx(trans)
                if res >= 0:
                    # total += len(trans)
                    total += res
        print(f'{dist} {self.name} trans {total}, throughput = {total*8/1000/1000/Ctrl.GetEndTime()}')
    def run(self, **kwargs):
        # self.throughputVsDistTest(Path.home()/'airsimNet'/'uav.csv')
        self.staticThroughputTest(**self.kwargs)
        # self.selfTest()