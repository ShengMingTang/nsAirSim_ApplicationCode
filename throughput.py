import matplotlib.pyplot as plt
import numpy as np
'''
{
	"SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
	"SettingsVersion": 1.2,
	"SimMode": "Multirotor",
	"ClockSpeed": 1,
	"CameraDefaults": {
		"CaptureSettings": [
		  {
			"ImageType": 0
		  }
		]
	},
	
	"Vehicles": {
		"A": {
		  "VehicleType": "SimpleFlight",
		  "X": 0, "Y": 0, "Z": 0
		}
    },

	"updateGranularity": 0.01,
            
	"segmentSize": 1448,
	"numOfCong": 0,
	"congRate": 1.0,
	"congArea": [0, 0, 10],
	
	"initEnbApPos": [
		[0, 0, 0]
	],

	"nRbs": 6,
	"TcpSndBufSize": 102400,
	"TcpRcvBufSize": 102400,
	"CqiTimerThreshold": 10,
	"LteTxPower": 0,
	"p2pDataRate": "10Gb/s",
	"p2pMtu": 1500,
	"p2pDelay": 1e-3,
	"useWifi": 0,
	
	"isMainLogEnabled": 1,
	"isGcsLogEnabled": 0,
	"isUavLogEnabled": 0,
	"isCongLogEnabled": 0,
	"isSyncLogEnabled": 0,

	"endTime": 5.0
}
'''
# Measure on receiver side
# In MBps
import matplotlib.pyplot as plt
import numpy as np
LTEIp = np.array([
    # [dist, throughput]
    # [250, 1.06395],
    # [1250, 0.533546],

    [0, 1.32964],
    [500, 0.812705],
    [1000, 0.555145],
    [1500, 0.446886],
    [2000, 0.294864],
    [2500, 0.293022],
    [3000, 0.24136],
    [3500, 0.203068],
    [4000, 0.203591],
    [4500, 0.0]
])
LTEApp = np.array([
    # [dist, throughput]
    # [250, 0.755],
    # [1250, 0.25180],
    
    [0, 1.09114],
    [500, 0.503606],
    [1000, 0.335737],
    [1500, 0.251803],
    [2000, 0.167868],
    [2500, 0.167868],
    [3000, 0.08393],
    [3500, 0.083934],
    [4000, 0.083934],
    [4500, 0.0]
])

plt.plot(LTEIp[:, 0], LTEIp[:, 1], 'o-', label='IP', linewidth=3, markersize=10)
plt.plot(LTEApp[:, 0], LTEApp[:, 1], 'X--', label='App', linewidth=3, markersize=10)
plt.ylabel('Throughput Mbps')
plt.xlabel('Distance (M)')
plt.legend()
plt.savefig('./throughput.eps')
plt.show()