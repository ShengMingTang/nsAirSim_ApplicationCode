import abc
import sys
from enum import Enum

class MsgBase(metaclass=abc.ABCMeta):
    '''
    Any application Msg should inherit this
    '''
    @abc.abstractmethod
    def GetTypeId(self):
        '''
        return an int ranging in (0,255]
        User is responsible for collision-free choice of TypeId
        '''
        return NotImplemented
    @abc.abstractmethod
    def serialize(self):
        '''
        return bytes representation of the obj itself
        '''
        return NotImplemented
    @classmethod
    @abc.abstractmethod
    def Deserialize(cls, data):
        '''
        classmethod (Of course, the object itself is not known before reconstructed)
        Take raw bytes as input and return the reconstructed object
        '''
        return NotImplemented
    @abc.abstractmethod
    def __str__(self):
        return NotImplemented

class AppSerializerState(Enum):
    '''
    State an AppSerializer may encounter
    '''
    TID = 0 # wait for typeId
    LEN = 1 # wait for len field
    DATA = 2 # wait for data
    CHECKSUM = 3 # wait for checksum
class AppSerializer():
    '''
    Responsible for serialize/deserialize obj
    '''
    TID_SIZE = 1
    LEN_SIZE = 4 # 4.29 GB
    CHECKSUM_SIZE = 1
    def __init__(self):
        self.buffer = bytes(0)
        # parsing self.buffer states
        self.state = AppSerializerState.TID
        self.stateTid = None
        self.stateLen = None
        self.stateData = bytes(0)
    def serialize(self, obj):
        '''
        serialize obj to specific format of bytes
        (typeId, len, bytes)
        raise TypeError obj is not an instance of MsgBase
        '''
        if isinstance(obj, MsgBase) is False:
            raise TypeError('obj should be an instance of MsgBase')
        tid = obj.GetTypeId().to_bytes(AppSerializer.TID_SIZE, byteorder=sys.byteorder, signed=False)
        bt = obj.serialize()
        length = len(bt).to_bytes(AppSerializer.LEN_SIZE, byteorder=sys.byteorder, signed=False)
        # @@ not implemented
        checksum = bytes(AppSerializer.CHECKSUM_SIZE)
        return tid + length + bt + checksum # concat
    def deserialize(self, bt):
        '''
        return an (typeId, bytes) if a complete obj is received
        return None on wait for more data transmitted

        its state may change during to process of parsing bytes
        '''
        self.buffer += bt
        # TID field is parsed
        if self.state == AppSerializerState.TID and len(self.buffer) >= AppSerializer.TID_SIZE:
            self.stateTid = int.from_bytes(self.buffer[:AppSerializer.TID_SIZE], byteorder=sys.byteorder, signed=False)
            self.buffer = self.buffer[AppSerializer.TID_SIZE:]
            self.state = AppSerializerState.LEN
            # print(f'Finish parsing TID {self.stateTid}')
        # LEN field is parsed
        if self.state == AppSerializerState.LEN and len(self.buffer) >= AppSerializer.LEN_SIZE:
            self.stateLen = int.from_bytes(self.buffer[:AppSerializer.LEN_SIZE], byteorder=sys.byteorder, signed=False)
            self.buffer = self.buffer[AppSerializer.LEN_SIZE:]
            self.state = AppSerializerState.DATA
            # print(f'Finish parsing LEN {self.stateLen}')
        # DATA field is parsed
        if self.state == AppSerializerState.DATA and len(self.buffer) >= self.stateLen:
            self.stateData = self.buffer[:self.stateLen]
            self.buffer = self.buffer[self.stateLen:]
            self.state = AppSerializerState.CHECKSUM
            # print(f'Finish parsing DATA {self.stateData}')
        if self.state == AppSerializerState.CHECKSUM and len(self.buffer) >= AppSerializer.CHECKSUM_SIZE:
            checksum = self.buffer[:AppSerializer.CHECKSUM_SIZE]
            self.buffer = self.buffer[AppSerializer.CHECKSUM_SIZE:]
            # @@ verify checksum
            ret = (self.stateTid, self.stateData)
            self.state = AppSerializerState.TID
            # print(f'Finish parsing CHECKSUM {checksum}')
            return ret # reconstruction is left to the application
        return None