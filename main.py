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

ctrl.Ctrl.SetEndTime(5.0)
context = zmq.Context()
json_path = f'{os.getenv("HOME")}/Documents/AirSim/settings.json'

netConfig = {
    'updateGranularity': 1.0,
    
    'segmentSize': 1448,
    'numOfCong': 1.0,
    'congRate': 1.0,
    'congArea': [0, 0, 10],
    
    #  uav names parsing
    'uavsName': [],
    # enb position parsing
    'initEnbPos': [
        [0, 0, 0],
		[0, 1, 0]
    ],

    "nRbs": 6, # see https://i.imgur.com/q55uR8T.png
    "TcpSndBufSize": 1024*70,
    "TcpRcvBufSize": 1024*70, # as long as it is larger than one picture
    "CqiTimerThreshold": 10,
    "LteTxPower": 0,
    "p2pDataRate": "10Gb/s",
    "p2pMtu": 1500,
    "p2pDelay": 1e-3,
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
kwargs = {"dist":2000}
gcsThread = gcs.Gcs(AIRSIM2NS_GCS_PORT, NS2AIRSIM_GCS_PORT, netConfig['uavsName'], context, **kwargs)
uavsThread = [ uav.Uav(name, AIRSIM2NS_PORT_START+i, NS2AIRSIM_PORT_START+i, context, **kwargs) for i, name in enumerate(netConfig['uavsName']) ]

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