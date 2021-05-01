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
    def __init__(self, name, zmqSendPort, zmqRecvPort, context):
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
    def Tx(self, payload, flags=zmq.NOBLOCK):
        try:
            self.zmqSendSocket.send(payload, flags=flags)
            res = self.zmqSendSocket.recv()
            res = int.from_bytes(res, 'little')
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
        self.Tx(b'I\'mm %b' % (bytes(self.name, encoding='utf-8')))
        s = self.Rx()
        while s == None:
            time.sleep(0.1)
            s = self.Rx()
        print(f'{self.name} recv: {s}')
    def throughputVsDistTest(self, filename, period=1.0, stay=2.0, step=50):
        with open(filename, 'w', newline='') as f:
            wrt = csv.writer(f)
            wrt.writerow(['Time', 'X', 'ByteCount'])
            pose = self.client.simGetVehiclePose(vehicle_name=self.name)
            pose.position.x_val = 0
            pose.position.y_val = 0
            pose.position.z_val = 0
            lastTx = Ctrl.GetSimTime()
            lastMv = lastTx
            while Ctrl.ShouldContinue():
                self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
                t = Ctrl.GetSimTime()
                if t - lastMv > stay:
                    pose.position.x_val += step
                    self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
                    lastMv = t
                if t - lastTx > period:
                    response = self.client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
                    res = self.Tx(bytes(response))
                    if res >= 0:
                        wrt.writerow([t, pose.position.x_val, len(bytes(response))])
    def run(self, **kwargs):
        self.throughputVsDistTest(Path.home()/'airsimNet'/'uav.csv')