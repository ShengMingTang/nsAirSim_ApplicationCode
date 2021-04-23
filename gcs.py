import setup_path
import airsim
import zmq
import threading
import time
import re
# custom import
from ctrl import Ctrl

class Gcs(threading.Thread):
    def __init__(self, zmqSendPort, zmqRecvPort, uavsName, context):
        threading.Thread.__init__(self)
        # socket need to be handled outside of this scope
        self.zmqSendSocket = context.socket(zmq.PUSH)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.uavsName = uavsName
        self.client = airsim.VehicleClient()
        self.client.confirmConnection()
    
    # parse <from-address> <payload>
    # return (from, payload) if successful otherwise return None
    def Rx(self, flags=zmq.NOBLOCK):
        try:
            return re.findall(r"[^ ]+", self.zmqRecvSocket.recv_string(flags))
        except zmq.Again:
            return None
    
    # transmit payload back to GCS
    # <payload> --- <sim_time> <name> <payload>
    def Tx(self, toName, payload):
        simTime = Ctrl.GetSimTime()

        s = f'{simTime} {toName} {payload}'
        self.zmqSendSocket.send(bytes(s, encoding='utf-8'))
        print(f'time {simTime}, GCS sends {s} to {toName}')
    
    def run(self):
        while Ctrl.GetSimTime() < 5:
            time.sleep(0.1)
        self.Tx("A", "Takeoff")
        self.Tx("B", "Land")
        while Ctrl.GetSimTime() < 10:
            time.sleep(0.1)
        self.Tx("A", "Land")
        self.Tx("B", "Takeoff")