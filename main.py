import zmq
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# custom import 
from app import GcsApp, UavApp
from msg import *
from ctrl import *

msgProtocol = {0:MsgRaw, 2:MsgImg}
context = zmq.Context(5)
json_path = Path.home()/'Documents'/'AirSim'/'settings.json'

ctrlThread = Ctrl(AIRSIM2NS_CTRL_PORT, NS2AIRSIM_CTRL_PORT, context)
netConfig = ctrlThread.sendNetConfig(json_path)


gcsThread = GcsApp(runner=GcsApp.streamingTest, msgProtocol=msgProtocol, isAddressPrefixed=True, zmqSendPort=AIRSIM2NS_GCS_PORT, zmqRecvPort=NS2AIRSIM_GCS_PORT, context=context)
uavsThread = [ UavApp(runner=UavApp.streamingTest, msgProtocol=msgProtocol, name=name, isAddressPrefixed=False, zmqSendPort=AIRSIM2NS_PORT_START+i, zmqRecvPort=NS2AIRSIM_PORT_START+i, context=context) for i, name in enumerate(netConfig['uavsName']) ]

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