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

NS2AIRSIM_PORT_START = 5000
AIRSIM2NS_PORT_START = 6000
NS2AIRSIM_GCS_PORT = 4999
AIRSIM2NS_GCS_PORT = 4998
NS2AIRSIM_CTRL_PORT = 8000
AIRSIM2NS_CTRL_PORT = 8001

context = zmq.Context()
json_path = f'{os.getenv("HOME")}/Documents/AirSim/settings.json'


# <- : nzmqIOthread segmentSize updateGranularity numOfCong congRate [congX congY congRho] numOfUav [name1 ]+ numOfEnb [px py pz ]+
netConfig = {
    'nzmqIOthread': 3,
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
}
print('Warning: nzmqIOthread is set but not used')
with open(json_path) as f:
    print(f'Using settings.json in {json_path}')
    settings = json.load(f)
    for key in netConfig:
        if key in settings:
            netConfig[key] = settings[key]
    netConfig['uavsName'] = [key for key in settings['Vehicles']]

ctrlThread = ctrl.Ctrl(AIRSIM2NS_CTRL_PORT, NS2AIRSIM_CTRL_PORT, context)
ctrlThread.sendNetConfig(netConfig)
print('========== Parsed config ==========')
for key in netConfig:
    print(f'{key}={netConfig[key]}')
print('========== ============= ==========')



gcsThread = gcs.Gcs(AIRSIM2NS_GCS_PORT, NS2AIRSIM_GCS_PORT, netConfig['uavsName'], context)
uavsThread = [ uav.Uav(name, AIRSIM2NS_PORT_START+i, NS2AIRSIM_PORT_START+i, context) for i, name in enumerate(netConfig['uavsName']) ]

ctrlThread.waitForSyncStart()
# NS will wait until AirSim sends back something from now on
ctrlThread.start()
gcsThread.start()
for td in uavsThread:
    td.start()
try:
    ctrlThread.join()
    gcsThread.join()
    for td in uavsThread:
        td.join()
finally :
    print("Canceled")
    ctrlThread.over()
    print('AirSim over!')
    sys.exit()
