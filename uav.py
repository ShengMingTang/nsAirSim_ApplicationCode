import setup_path
import airsim
import zmq
import threading
import re
import time
# custom import
from ctrl import Ctrl

class Uav(threading.Thread):
    def __init__(self, name, zmqSendPort, zmqRecvPort, context):
        threading.Thread.__init__(self)
        # socket need to be handled outside of this scope
        self.name = name
        self.zmqSendSocket = context.socket(zmq.PUSH)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
    # parse <from-address> <payload>
    # return (from, payload) if successful otherwise return None
    def Rx(self, flags=zmq.NOBLOCK):
        try:
            s = self.zmqRecvSocket.recv(flags)
            # @@
            # s = re.findall(r"[^ ]+", self.zmqRecvSocket.recv_string(flags))
            return s
        except zmq.Again:
            return None

    # transmit payload back to GCS
    # this function add some co-sim encoding
    # <simTime> <payload>
    # Packets will be transmitted only if NS has set up everything
    # It can still be called
    def Tx(self, payload, flags=zmq.NOBLOCK):
        try:
            simTime = Ctrl.GetSimTime()
            s = b'%.2f %b' % (simTime, payload)
            self.zmqSendSocket.send(s, flags=flags)
            print('time: %.2f, %s send:%d' % (simTime, self.name, len(s)))
        except zmq.Again:
            return None
    
    def throughputTest(self, dist=0.0):
        self.dist = dist
        pose = self.client.simGetVehiclePose(vehicle_name=self.name)
        pose.position.x_val = self.dist
        pose.position.y_val = 0
        pose.position.z_val = 0
        self.client.enableApiControl(True, vehicle_name=self.name)
        self.client.armDisarm(True, vehicle_name=self.name)
    
    def run(self):
        # custom code below
        # self.client.takeoffAsync(vehicle_name=self.name).join()
        # self.client.moveByVelocityBodyFrameAsync(20, 0, 0, 500, vehicle_name=self.name)
        lastTx = Ctrl.GetSimTime()
        while Ctrl.ShouldContinue():
            t = Ctrl.GetSimTime() 
            if t - lastTx > 0.01:
                response = self.client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
                self.Tx(bytes(response))
                lastTx = t
        print(self.name, ' join')