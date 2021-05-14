import sys, inspect
import numpy as np
from appProtocolBase import MsgBase, MsgRaw
import pickle

'''
Custom message
'''

class MsgImg(MsgBase):
    def __init__(self, png=np.zeros((0,)), timestamp=0.0, **kwargs):
        self.png = png
        self.timestamp = timestamp
    @classmethod
    def GetTypeId(self):
        return 2
    def serialize(self):
        return pickle.dumps(self)
    @classmethod
    def Deserialize(cls, data):
        return pickle.loads(data)
    def __str__(self):
        return f'ts:{self.timestamp}, img size:{np.size(self.png)}'

# summary
MsgSerializers = {}
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and issubclass(obj, MsgBase):
        if obj != MsgBase:
            if obj().GetTypeId() in MsgSerializers:
                raise ValueError(f'{obj().GetTypeId()} is already registered')
            else:
                MsgSerializers[obj().GetTypeId()] = obj
 