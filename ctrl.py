import setup_path
import airsim
import threading
import re
import zmq
import time
import sys

NS2AIRSIM_PORT_START = 5000
AIRSIM2NS_PORT_START = 6000
NS2AIRSIM_GCS_PORT = 4999
AIRSIM2NS_GCS_PORT = 4998
NS2AIRSIM_CTRL_PORT = 8000
AIRSIM2NS_CTRL_PORT = 8001
GCS_APP_START_TIME = 0.1
UAV_APP_START_TIME = 0.2

CLEAN_UP_TIME = 1.0

class Ctrl(threading.Thread):
    endTime = 0.1
    mutexSimTime = threading.Lock()
    simTime = 0
    lastTimestamp = time.time()
    isRunning = True
    def __init__(self, zmqSendPort, zmqRecvPort, context):
        threading.Thread.__init__(self)
        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.zmqRecvSocket.setsockopt(zmq.RCVTIMEO, 1000)

        self.zmqSendSocket = context.socket(zmq.PUSH)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.simRunConsoleCommand('stat fps')
    
    @staticmethod
    def ShouldContinue():
        return Ctrl.isRunning and Ctrl.GetSimTime() < Ctrl.GetEndTime()
    @staticmethod
    # Extra cleanup time is granted for cleaning its receiving buffer 
    def ShouldContinueAndCleanUp():
        return Ctrl.GetSimTime() < Ctrl.GetEndTime() + CLEAN_UP_TIME
    
    @staticmethod
    def SetEndTime(endTime):
        Ctrl.mutexSimTime.acquire()
        Ctrl.endTime = endTime
        Ctrl.mutexSimTime.release()

    @staticmethod
    def GetEndTime():
        Ctrl.mutexSimTime.acquire()
        temp = Ctrl.endTime
        Ctrl.mutexSimTime.release()
        return temp
    @staticmethod
    def GetSimTime():
        Ctrl.mutexSimTime.acquire()
        temp = Ctrl.simTime
        Ctrl.mutexSimTime.release()
        return temp
    # get continuous version of time
    @staticmethod
    def GetFineTime():
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
    def sendNetConfig(self, netConfig):
        self.netConfig = netConfig
        s = ''
        s += f'{netConfig["useWifi"]} '
        s += f'{netConfig["isMainLogEnabled"]} {netConfig["isGcsLogEnabled"]} {netConfig["isUavLogEnabled"]} {netConfig["isCongLogEnabled"]} {netConfig["isSyncLogEnabled"]} '
        s += f'{netConfig["segmentSize"]} {netConfig["updateGranularity"]} {netConfig["numOfCong"]} {netConfig["congRate"]} {netConfig["congArea"][0]} {netConfig["congArea"][1]} {netConfig["congArea"][2]} '
        s += f'{len(netConfig["uavsName"])} '
        for name in netConfig["uavsName"]:
            s += f'{name} '
        s += f'{len(netConfig["initEnbPos"])} '
        for pos in netConfig["initEnbPos"]:
            s += f'{pos[0]} {pos[1]} {pos[2]} '
        self.zmqSendSocket.send_string(s)
    
    def run(self):
        while Ctrl.ShouldContinue():
            # Never wait if AirSim is assumed to be run no faster than realtime
            msg = self.zmqRecvSocket.recv()
            # this will block until resumed
            self.client.simContinueForTime(self.netConfig['updateGranularity'])
            Ctrl.mutexSimTime.acquire()
            Ctrl.simTime += self.netConfig['updateGranularity']
            Ctrl.lastTimestamp = time.time()
            Ctrl.mutexSimTime.release()
            self.zmqSendSocket.send_string('')
            # print(f'Time = {Ctrl.GetSimTime()}')
        Ctrl.isRunning = False
        self.zmqSendSocket.send_string('')
        self.zmqSendSocket.send_string(f'bye {Ctrl.GetEndTime()}')
        while Ctrl.ShouldContinueAndCleanUp():
            self.client.simContinueForTime(self.netConfig['updateGranularity'])
            Ctrl.mutexSimTime.acquire()
            Ctrl.simTime += self.netConfig['updateGranularity']
            Ctrl.lastTimestamp = time.time()
            Ctrl.mutexSimTime.release()