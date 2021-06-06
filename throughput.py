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
LTEIp = np.array([
    # [dist, throughput]
    [0, 1.32964],
    [250, 1.06395],
    [500, 0.812705],
    [750, 0.640659],
    [1000, 0.556357],
    [1250, 0.533546],
    [2000, 0.2954],
    [3000, 0.2413],
])
LTEApp = np.array([
    # [dist, throughput]
    [0, 1.09114],
    [250, 0.755],
    [500, 0.5036],
    [1000, 0.335737],
    [1250, 0.25180],
    [2000, 0.167868],
    [3000, 0.08393]
])

plt.plot(LTEIp[:, 0], LTEIp[:, 1], 'x-', label='LTE IP level')
plt.plot(LTEApp[:, 0], LTEApp[:, 1], 'x-', label='LTE App level')
plt.title('Throughput vs distance')
plt.ylabel('Mbps')
plt.xlabel('distance (in meters)')
plt.legend()
plt.savefig('./throughput.png')
plt.show()