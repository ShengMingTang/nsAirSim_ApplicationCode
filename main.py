import setup_path
import airsim
import zmq
import re
import time
import threading
import sys
import json
import os
from pathlib import Path
# custom import 
import gcs
import uav
import ctrl
from ctrl import NS2AIRSIM_PORT_START, AIRSIM2NS_PORT_START, NS2AIRSIM_GCS_PORT, AIRSIM2NS_GCS_PORT, NS2AIRSIM_CTRL_PORT, AIRSIM2NS_CTRL_PORT

kwargs = {"dist":0}

context = zmq.Context()
json_path = Path.home()/'Documents'/'AirSim'/'settings.json'

ctrlThread = ctrl.Ctrl(AIRSIM2NS_CTRL_PORT, NS2AIRSIM_CTRL_PORT, context)
netConfig = ctrlThread.sendNetConfig(json_path)
gcsThread = gcs.Gcs(AIRSIM2NS_GCS_PORT, NS2AIRSIM_GCS_PORT, netConfig['uavsName'], context, **kwargs)
uavsThread = [ uav.Uav(name, AIRSIM2NS_PORT_START+i, NS2AIRSIM_PORT_START+i, context, **kwargs) for i, name in enumerate(netConfig['uavsName']) ]

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
sys.exit()