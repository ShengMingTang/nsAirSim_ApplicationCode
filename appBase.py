import abc
import zmq
import sys
import re
import threading
import queue
import time
from appProtocolBase import AppSerializer, MsgBase, 
from ctrl import Ctrl

IOTIMEO = 1000 # I/O timeout for AppReceiver and AppSender

class AppReceiver(threading.Thread):
    '''
    This thread runs as an attribute of AppBase to receive bytes in the background
    isAddressPrefixed: True then all byte I/O will be prefixed with toName/fromName
    zmqLevel transmission syntax: (name)?[ ](bytes)
    zmqRecvPort, context
    '''
    def __init__(self, isAddressPrefixed, zmqRecvPort, context, msgProtocol, **kwargs):
        super().__init__()
        self.mutex = threading.Lock()
        self.isAddressPrefixed = isAddressPrefixed
        self.desrler = AppSerializer()
        self.deSrlers = {}
        self.msgs = queue.Queue()
        self.stopFlag = False
        self.msgProtocol = msgProtocol
        
        self.zmqRecvSocket = context.socket(zmq.PULL)
        self.zmqRecvSocket.connect(f'tcp://localhost:{zmqRecvPort}')
        self.zmqRecvSocket.setsockopt(zmq.RCVTIMEO, IOTIMEO)
    def recvMsg(self):
        '''
        return FIFO scheme complete MsgBase object in self.msgs if addressNotPrefixed
        return (addr, MsgBase) if address is prefixed      
        return None if no complete MsgBase object is received
        '''
        try:
            if self.isAddressPrefixed:
                addr, data = self.msgs.get_nowait()
                tid, bt = data
                return (addr, self.msgProtocol[tid].Deserialize(bt))
            else:
                data = self.msgs.get_nowait()
                tid, bt = data
                return self.msgProtocol[tid].Deserialize(bt)
        except queue.Empty:
            return None
    def setStopFlag(self):
        '''
        must be called if receiving process is about to end
        this thread will not join successfully if stopFlag is not set
        '''
        with self.mutex:
            self.stopFlag = True
    def run(self, **kwargs):
        '''
        run until stopFlag is set
        keep receiving raw bytes and push them into self.msgs in FIFO scheme
        use self.recvMsg() to retrieve MsgBase obj
        '''
        while self.stopFlag is False:
            try:
                fromName = None
                msg = self.zmqRecvSocket.recv()
                if self.isAddressPrefixed:
                    s, e = re.search(b" ", msg).span()
                    fromName = msg[:s].decode('ascii')
                    msg = msg[s+1:]
                    if fromName not in self.deSrlers:
                        self.deSrlers[fromName] = AppSerializer()
                    data = self.deSrlers[fromName].deserialize(msg)
                    if data is not None:
                        self.msgs.put_nowait((fromName, data))
                else:
                    data = self.desrler.deserialize(msg)
                    if data is not None:
                        self.msgs.put_nowait(data)
            except:
                pass

class AppSender(threading.Thread):
    def __init__(self, isAddressPrefixed, zmqSendPort, context, **kwargs):
        super().__init__()
        self.mutex = threading.Lock()
        self.isAddressPrefixed = isAddressPrefixed
        self.srler = AppSerializer()
        self.msgs = queue.Queue()
        self.packetSize = Ctrl.GetNetConfig()['TcpSndBufSize'] // 5
        self.lastPacket = None
        self.packets = queue.Queue()
        self.stopFlag = False
        self.count = 0
                
        self.zmqSendSocket = context.socket(zmq.REQ)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqSendSocket.setsockopt(zmq.RCVTIMEO, IOTIMEO)
    def sendMsg(self, msg, toName):
        if self.isAddressPrefixed is False and toName is not None:
            raise ValueError('isAddressPrefixed False but toName is specified')
        elif self.isAddressPrefixed is True and toName is None:
            raise ValueError('isAddressPrefixed True but toName is NOT specified')
        
        with self.mutex:
            stopFlag = self.stopFlag
            count = self.count
            self.count += 1
        if stopFlag is False:
            try:
                self.msgs.put_nowait((count, msg, toName))
                return True
            except queue.Full:
                return False
        return False
    def flushMsgs(self):
        with self.mutex:
            while self.msgs.empty() is False:
                self.msgs.get_nowait()
    def setStopFlag(self):
        '''
        must be called if receiving process is about to end
        this thread will not join successfully if stopFlag is not set
        '''
        with self.mutex:
            self.stopFlag = True
    def run(self, **kwargs):
        while self.stopFlag is False:
            if self.lastPacket is None: # last one is finished
                if self.packets.empty() is False: # we have next one to transmit
                    self.lastPacket = self.packets.get_nowait()
                else: # decompose next msg if any
                    try:
                        c, msg, toName = self.msgs.get(True, IOTIMEO/1000)
                        bt = self.srler.serialize(msg)
                        # decompose to packets
                        for i in range(0, len(bt), self.packetSize):
                            self.packets.put_nowait((toName, bt[i*self.packetSize:(i+1)*self.packetSize]))
                    except queue.Empty:
                        pass
            else: # proceed to next one
                toName, payload = self.lastPacket
                if toName is not None:
                    payload = b'%b %b' % (bytes(toName, encoding='utf-8'), payload)
                    # print(toName, payload)
                try:
                    self.zmqSendSocket.send(payload, flags=zmq.NOBLOCK)    
                    res = self.zmqSendSocket.recv()
                    res = int.from_bytes(res, sys.byteorder, signed=True)
                    if res >= 0: # success, jump to next packet
                        self.lastPacket = None
                except zmq.ZMQError:
                    pass
class AppBase(metaclass=abc.ABCMeta):
    '''
    Any custom level application must inherit this
    implement Tx/Rx functions
    '''
    def __init__(self, zmqSendPort, context, **kwargs):
        super().__init__()
        self.zmqSendSocket = context.socket(zmq.REQ)
        self.zmqSendSocket.bind(f'tcp://*:{zmqSendPort}')
        self.zmqSendSocket.setsockopt(zmq.RCVTIMEO, 1000)
        self.srler = AppSerializer()
        self.recvThread = AppReceiver(context=context, **kwargs)
    def Tx(self, obj, toName=None, flags=zmq.NOBLOCK):
        '''
        use MsgRaw as default type of Msg passing
        raise TypeError if toName is specified in UAV mode (isAddressPrefixed set to False)
        return int as the same in ns socket->Send()
        '''
        if isinstance(obj, MsgBase) is False:
            obj = MsgRaw(obj)
        # serialize
        payload = self.srler.serialize(obj)
        if toName is not None:
            if self.recvThread.isAddressPrefixed is False:
                raise TypeError('isAddressPrefixed set to False but desition is specified')
            payload = b'%b %b' % (bytes(toName, encoding='utf-8'), payload)
        try:
            self.zmqSendSocket.send(payload, flags=flags)
            res = self.zmqSendSocket.recv()
            res = int.from_bytes(res, sys.byteorder, signed=True)
            return res
        except zmq.ZMQError:
            return -1
    def Rx(self):
        '''
        return None if a complete MsgBase is not received
        else
        return MsgBase if isAddressPrefixed is False
        return (fromName, MsgBase) otherwise
        '''      
        return self.recvThread.recvMsg()
    @abc.abstractmethod
    def run(self, **kwargs):
        '''
        # Template
        # Add small amount of delay(1.0s) before transmitting anything
        # This is for ns to have time to set up everything
        Ctrl.Wait(1.0)

        self.recvThread.start()
        
        # custom code
        self.customFn()
        # custom code
        
        self.recvThread.setStopFlag()
        self.recvThread.join()
        
        self.customFn():
            self.client.enableApiControl(True, vehicle_name=self.name)
            self.client.armDisarm(True, vehicle_name=self.name)
        '''
        return NotImplemented
