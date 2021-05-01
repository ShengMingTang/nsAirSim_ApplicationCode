import setup_path
import airsim
import zmq
import re
import time
import threading
import sys
import json
import os
# custom import 
import gcs
import uav
import ctrl
from ctrl import NS2AIRSIM_PORT_START, AIRSIM2NS_PORT_START, NS2AIRSIM_GCS_PORT, AIRSIM2NS_GCS_PORT, NS2AIRSIM_CTRL_PORT, AIRSIM2NS_CTRL_PORT

ctrl.Ctrl.SetEndTime(2.0*1)
context = zmq.Context()
json_path = f'{os.getenv("HOME")}/Documents/AirSim/settings.json'

netConfig = {
    'segmentSize': 1448,
    'updateGranularity': 1.0,
    'numOfCong': 1.0,
    'congRate': 1.0,
    'congArea': [0, 0, 10],
    'uavsName': [],
    'initEnbPos': [
        [0, 0, 0],
		[0, 1, 0]
    ],
    "useWifi": 0,
    "isMainLogEnabled": 1,
	"isGcsLogEnabled": 0,
	"isUavLogEnabled": 1,
	"isCongLogEnabled": 0,
	"isSyncLogEnabled": 0,
}
with open(json_path) as f:
    print(f'Using settings.json in {json_path}')
    settings = json.load(f)
    for key in netConfig:
        if key in settings:
            netConfig[key] = settings[key]
    netConfig['uavsName'] = [key for key in settings['Vehicles']]
print('========== Parsed config ==========')
print(netConfig)
print('========== ============= ==========')

ctrlThread = ctrl.Ctrl(AIRSIM2NS_CTRL_PORT, NS2AIRSIM_CTRL_PORT, context)
gcsThread = gcs.Gcs(AIRSIM2NS_GCS_PORT, NS2AIRSIM_GCS_PORT, netConfig['uavsName'], context)
uavsThread = [ uav.Uav(name, AIRSIM2NS_PORT_START+i, NS2AIRSIM_PORT_START+i, context) for i, name in enumerate(netConfig['uavsName']) ]

ctrlThread.sendNetConfig(netConfig)
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