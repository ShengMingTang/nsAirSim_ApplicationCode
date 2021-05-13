import setup_path
import airsim
import zmq
import threading
import sys
import queue
from pathlib import Path

# custom import 
from app import GcsApp, UavApp
import ctrl
from ctrl import NS2AIRSIM_PORT_START, AIRSIM2NS_PORT_START, NS2AIRSIM_GCS_PORT, AIRSIM2NS_GCS_PORT, NS2AIRSIM_CTRL_PORT, AIRSIM2NS_CTRL_PORT
import matplotlib.pyplot as plt
import numpy as np

kwargs = {"dist":0}

context = zmq.Context()
json_path = Path.home()/'Documents'/'AirSim'/'settings.json'

ctrlThread = ctrl.Ctrl(AIRSIM2NS_CTRL_PORT, NS2AIRSIM_CTRL_PORT, context)
netConfig = ctrlThread.sendNetConfig(json_path)


gcsThread = GcsApp(isAddressPrefixed=True, zmqSendPort=AIRSIM2NS_GCS_PORT, zmqRecvPort=NS2AIRSIM_GCS_PORT, context=context)
uavsThread = [ UavApp(name=name, isAddressPrefixed=False, zmqSendPort=AIRSIM2NS_PORT_START+i, zmqRecvPort=NS2AIRSIM_PORT_START+i, context=context, **kwargs) for i, name in enumerate(netConfig['uavsName']) ]

ctrlThread.waitForSyncStart()

# NS will wait until AirSim sends back something from now on

ctrlThread.start()
gcsThread.start()
for td in uavsThread:
    td.start()      

ctrlThread.join()
gcsThread.join()
for td in uavsThread:
    td.join()

plt.clf()
sys.exit()