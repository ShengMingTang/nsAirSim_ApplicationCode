import setup_path
import airsim
import threading
import re
import zmq
import time

class Ctrl(threading.Thread):
    mutexSimTime = threading.Lock()
    simTime = 0
    lastTimestamp = time.time()
    def __init__(self, zmqSendPort, zmqRecvPort, context):
        threading.Thread.__init__(self)
        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.zmqSendSocket = context.socket(zmq.PUSH)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.simRunConsoleCommand('stat fps')
    
    @staticmethod
    def GetSimTime():
        Ctrl.mutexSimTime.acquire()
        temp = Ctrl.simTime + (time.time() - Ctrl.lastTimestamp)
        Ctrl.mutexSimTime.release()
        return temp

    # to synchronize start
    # Corresponds to nsAirSimBegin() in AirSimSync.cc
    def waitForSyncStart(self):
        self.zmqRecvSocket.recv()
        self.client.reset()
        self.client.simPause(False)
        # static member init
        Ctrl.mutexSimTime.acquire()
        Ctrl.simTime = 0
        Ctrl.lastTimestamp = time.time()
        Ctrl.mutexSimTime.release()
    
    def over(self):
        self.zmqSendSocket.send_string('End')
    
    def concatString(self, obj):
        try:
            s = ''
            for dummy in obj:
                s += self.iterableToString(dummy)
            return s
        except: # non-iterable
            return f'{obj} '

    def sendNetConfig(self, netConfig):
        self.netConfig = netConfig

        s = f'{netConfig["nzmqIOthread"]} {netConfig["segmentSize"]} {netConfig["updateGranularity"]} {netConfig["numOfCong"]} {netConfig["congRate"]} {netConfig["congArea"][0]} {netConfig["congArea"][1]} {netConfig["congArea"][2]} '
        s += f'{len(netConfig["uavsName"])} '
        for name in netConfig["uavsName"]:
            s += f'{name} '
        s += f'{len(netConfig["initEnbPos"])} '
        for pos in netConfig["initEnbPos"]:
            s += f'{pos[0]} {pos[1]} {pos[2]} '
        self.zmqSendSocket.send_string(s)
    
    def run(self):
        while True:
            # Never wait if AirSim is assumed to be run no faster than realtime
            msg = self.zmqRecvSocket.recv()
            
            # this will block until resumed
            self.client.simContinueForTime(self.netConfig['updateGranularity'])
            Ctrl.mutexSimTime.acquire()
            Ctrl.simTime += self.netConfig['updateGranularity']
            Ctrl.lastTimestamp = time.time()
            Ctrl.mutexSimTime.release()
            self.zmqSendSocket.send_string('')
            print(f'Time = {Ctrl.GetSimTime()}')