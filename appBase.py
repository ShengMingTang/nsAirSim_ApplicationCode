import abc
import zmq
import sys
import re
import threading
import queue
from appProtocolBase import AppSerializer, MsgBase, MsgRaw

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
        self.zmqRecvSocket.setsockopt(zmq.RCVTIMEO, 1000)
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
        self.mutex.acquire()
        self.stopFlag = True
        self.mutex.release()
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
                        self.mutex.acquire()
                        self.msgs.put_nowait((fromName, data))
                        self.mutex.release()
                else:
                    data = self.desrler.deserialize(msg)
                    if data is not None:
                        self.mutex.acquire()
                        self.msgs.put_nowait(data)
                        self.mutex.release()
            except:
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
        return (typeId, len, data) if isAddressPrefixed is False
        return (fromName, typeId, len, data) otherwise
        '''
        return self.recvThread.recvMsg()
    @abc.abstractmethod
    def run(self, **kwargs):
        '''
        Template
        self.recvThread.start()
        # custom code
        self.customFn()
        # custom code
        self.recvThread.setStopFlag()
        self.recvThread.join()
        
        self.customFn():
            self.client.enableApiControl(True, vehicle_name=self.name)
            self.client.armDisarm(True, vehicle_name=self.name)
            *Add small amount of delay(1.0s) before transmitting anything*
        '''
        return NotImplemented
