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
            s = re.findall(r"[^ ]+", self.zmqRecvSocket.recv_string(flags))
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

            s = f'{simTime} {payload}'
            self.zmqSendSocket.send(bytes(s, encoding='utf-8'), flags=flags)
            print(f'time: {simTime}, {self.name} sends {s}')
        except zmq.Again:
            return None
    
    def run(self):
        self.client.enableApiControl(True, vehicle_name=self.name)
        self.client.armDisarm(True, vehicle_name=self.name)
      
        while True:
            packet = self.Rx(zmq.NOBLOCK)
            if packet:
                address, cmd = packet
                if cmd == 'Land':
                    print(f'{self.name}: cmd={cmd}')
                    self.client.landAsync(vehicle_name=self.name).join()
                    # self.client.moveByVelocityBodyFrameAsync(1, 0, 0, 10.0, vehicle_name=self.name).join()
                elif cmd == 'Takeoff':
                    print(f'{self.name}: cmd={cmd}')
                    self.client.takeoffAsync(vehicle_name=self.name).join()
                    # self.client.moveByVelocityBodyFrameAsync(-1, 0, 0, 10.0, vehicle_name=self.name).join()