import setup_path
import airsim
import zmq
import threading
import time
import re
from pathlib import Path
import csv
from functools import partial
# custom import
from ctrl import Ctrl

class Gcs(threading.Thread):
    def __init__(self, zmqSendPort, zmqRecvPort, uavsName, context):
        threading.Thread.__init__(self)
        # socket need to be handled outside of this scope
        self.zmqSendSocket = context.socket(zmq.REQ)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqSendSocket.setsockopt(zmq.RCVTIMEO, 1000)

        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.uavsName = uavsName
        self.client = airsim.VehicleClient()
        self.client.confirmConnection()
    def Tx(self, toName, payload, flags=zmq.NOBLOCK):
        try:
            self.zmqSendSocket.send(b'%b %b' % (bytes(toName, encoding='utf-8'), payload), flags=flags)
            res = self.zmqSendSocket.recv()
            res = int.from_bytes(res, 'little')
            return res
        except zmq.ZMQError:
            return -1
    def Rx(self, flags=zmq.NOBLOCK):
        try:
            msg = self.zmqRecvSocket.recv(flags)
            s, e = re.search(b" ", msg).span()
            return msg[:s], msg[s:]
        except zmq.ZMQError:
            return None
    def selfTest(self):
        while Ctrl.GetSimTime() < 1.0:
            time.sleep(0.1)
        self.Tx('ABCD', b'I\'m GCS')
        s = self.Rx()
        while s == None:
            time.sleep(0.1)
            s = self.Rx()
        print(f'GCS recv: {s}')
    def throughputVsDistTest(self, filename, period=0.01, stay=2.0, step=50):
        while Ctrl.GetSimTime() < 1.0:
            time.sleep(0.1)
        self.Tx('ABCD', b'I\'m GCS')
        with open(filename, 'w', newline='') as f:
            wrt = csv.writer(f)
            wrt.writerow(['Time', 'who', 'ByteCount'])
            while Ctrl.ShouldContinue():
                whoPkt = self.Rx()
                t = Ctrl.GetSimTime()
                if whoPkt != None:
                    who, pkt = whoPkt
                    bt = len(pkt)
                    wrt.writerow([t, who.decode('ascii'), bt])
    def run(self):
        self.throughputVsDistTest(Path.home()/'airsimNet'/'gcs.csv')