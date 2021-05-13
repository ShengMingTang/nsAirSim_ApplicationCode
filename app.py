import setup_path
import airsim
import threading
import time
import cv2
import numpy as np
import matplotlib.pyplot as plt

from appProtocolBase import AppSerializer, MsgBase, MsgRaw
from ctrl import Ctrl
from appBase import AppBase
from msg import MsgImg, MsgSerializers

'''
Custom App code
'''

class UavApp(AppBase, threading.Thread):
    def __init__(self, name, **kwargs):
        '''
        UavApp(name=name, isAddressPrefixed=False, zmqSendPort=AIRSIM2NS_PORT_START+i, zmqRecvPort=NS2AIRSIM_PORT_START+i, context=context)
        '''
        super().__init__(**kwargs)
        self.name = name
        self.kwargs = kwargs
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
    def selfTest(self, **kwargs):
        '''
        Basic utility test including Tx, Rx, MsgRaw
        paired with GcsApp.selfTest()
        '''
        Ctrl.Wait(1.0)
        msg = MsgRaw(b'I\'m %b' % (bytes(self.name, encoding='utf-8')))
        # msg = MsgImg(np.zeros((3,3), dtype=np.uint8), 0.0)
        res = -1
        while res == -1:
            res = self.Tx(msg)
        reply = None
        while Ctrl.ShouldContinue() and reply is None:
            reply = self.Rx()
        if reply is not None:
            t, d = reply
            reply = MsgSerializers[t].Deserialize(d)
            print(f'{self.name} recv: {reply}')
    def staticThroughputTest(self, dist, period=0.01, **kwargs):
        '''
        Run throughput test at application level
        dist argument must be specified
        paired with GcsApp.staticThroughputTest()
        '''
        total = 0
        pose = self.client.simGetVehiclePose(vehicle_name=self.name)
        pose.position.x_val = dist
        lastTx = Ctrl.GetSimTime()
        msg = MsgRaw(bytes(50*1024))
        self.client.simSetVehiclePose(pose, True, vehicle_name=self.name)
        delay = 1.0
        Ctrl.Wait(delay)
        while Ctrl.ShouldContinue():
            t = Ctrl.GetSimTime()
            if t - lastTx > period:
                res = self.Tx(msg)
                if res >= 0:
                    total += res
        print(f'{dist} {self.name} trans {total}, throughput = {total*8/1000/1000/(Ctrl.GetEndTime()-delay)}')
    def streamingTest(self, **kwargs):
        '''
        Test Msg Level streaming back to GCS
        '''
        self.client.enableApiControl(True, vehicle_name=self.name)
        self.client.armDisarm(True, vehicle_name=self.name)
        
        Ctrl.Wait(1.0)
        # self.client.takeoffAsync(vehicle_name=self.name).join()
        # self.client.moveByVelocityBodyFrameAsync(5, 0, 0, 20, vehicle_name=self.name)
        while Ctrl.ShouldContinue():
            Ctrl.Wait(0.1)
            rawImage = self.client.simGetImage("0", airsim.ImageType.Scene, vehicle_name=self.name)
            png = cv2.imdecode(airsim.string_to_uint8_array(rawImage), cv2.IMREAD_UNCHANGED)
            msg = MsgImg(png, Ctrl.GetSimTime())
            res = self.Tx(msg)
            # print(f'res = {res}')
    def run(self, **kwargs):
        self.recvThread.start()
        self.selfTest(**self.kwargs)
        # self.staticThroughputTest(**self.kwargs)
        # self.streamingTest(**self.kwargs)
        self.recvThread.setStopFlag()
        self.recvThread.join()
        print(f'{self.name} joined')
        
class GcsApp(AppBase, threading.Thread):
    def __init__(self, **kwargs):
        '''
        GcsApp(isAddressPrefixed=True, zmqSendPort=AIRSIM2NS_GCS_PORT, zmqRecvPort=NS2AIRSIM_GCS_PORT, context=context)
        '''
        super().__init__(**kwargs)
        self.name = 'GCS'
        self.kwargs = kwargs
    def selfTest(self, **kwargs):
        '''
        Basic utility test including Tx, Rx, MsgRaw
        paired with UavApp.selfTest()
        '''
        Ctrl.Wait(1.0)
        res = -1
        while res == -1:
            res = self.Tx(b'I\'m GCS', 'A')
        print(f'GCS trans to A with res {res}')
        res = -1
        while res == -1:
            res = self.Tx(b'I\'m GCS', 'B')
        print(f'GCS trans to B with res {res}')
        while Ctrl.ShouldContinue():
            reply = self.Rx()
            if reply is None:
                time.sleep(0.1)
            else:
                name, msg = reply
                t, d = msg
                reply = MsgSerializers[t].Deserialize(d)
                print(f'{self.name} recv: {reply} from {name}')
    def staticThroughputTest(self, **kwargs):
        '''
        Run throughput test at application level
        paired with UavApp.staticThroughputTest()
        '''
        total = 0
        delay = 1.0
        while Ctrl.ShouldContinue():
            msg = self.Rx()
            if msg is not None:
                addr, msg = msg
                t, d = msg
                msg = MsgRaw(d)
                total += len(msg.data)
        print(f'GCS recv {total}, throughput = {total*8/1000/1000/(Ctrl.GetEndTime()-delay)}')
    def streamingTest(self, **kwargs):
        '''
        Test Msg Level streaming back to GCS
        '''
        # @@ matplotlib lib is not thread safe, RuntimeError will be raised at the end of simulation
        fig = None
        while Ctrl.ShouldContinue():
            reply = self.Rx()
            if reply is not None:
                name, msg = reply
                t, d = msg
                reply = MsgSerializers[t].Deserialize(d)
                # print(f'GCS recv {reply}')
                
                if fig is None:
                    fig = plt.imshow(reply.png)
                else:
                    fig.set_data(reply.png)
            else:
                pass
            plt.pause(0.1)
            plt.draw()
        plt.clf()
    def run(self, **kwargs):
        self.recvThread.start()
        self.selfTest(**self.kwargs)
        # self.staticThroughputTest(**self.kwargs)
        # self.streamingTest(**self.kwargs)
        self.recvThread.setStopFlag()
        self.recvThread.join()
        print(f'{self.name} joined')