import matplotlib.pyplot as plt
import csv
import numpy as np
import pandas as pd
import math
from pathlib import Path

ROOT = Path.home()/'airsimNet'

times = []
mob = []
lastX = 0 # assume initX = 0


with open(ROOT/'nsAirSim_mobility.csv', 'r') as f:
    rows = csv.reader(f, delimiter=' ')
    header = next(rows)
    # Time name x y z
    for row in rows:
        t, x, y, z = float(row[0]), float(row[2]), float(row[3]), float(row[4])
        if abs(x-lastX) >= 1:
            times.append(t)
            mob.append(lastX)
            lastX = x
times = np.array(times)
times[-1] = 1e9 # count to infinity
mob = np.array(mob)
# print(len(times))
# print(mob)

# dist: [start, end, bytes]
pSet = {}
pDrop = {}
sendIntervals = [[1e9, -1, 0] for i in range(len(mob))]
recvIntervals = [[1e9, -1, 0] for i in range(len(mob))]
sendLastIdx = 0
recvLastIdx = 0
with open(ROOT/'nsAirSim_throughput.csv', 'r') as f:
    rows = csv.reader(f, delimiter=' ')
    header = next(rows)
    # Time packetId name TxRx ByteCount
    for row in rows:
        t, p, name, tr, b = float(row[0]), int(row[1]), row[2], row[3], int(row[4])
        
        if name == 'ABCD' and tr == 'Tx': # count that
            if t > times[sendLastIdx]:
                sendLastIdx += 1
            s, e, bt = sendIntervals[sendLastIdx]
            s = min(s, t)
            e = max(e, t)
            bt += b
            sendIntervals[sendLastIdx] = [s, e, bt]
            pSet[p] = t
            if p not in pDrop:
                pDrop[p] = 0
            pDrop[p] += b
        
        
        if name == 'G' and tr == 'Rx': # count that
            if p in pSet and pSet[p] > times[recvLastIdx]:
                recvLastIdx += 1
            if p in pSet:
                s, e, bt = recvIntervals[recvLastIdx]
                s = min(s, t)
                e = max(e, t)
                bt += b
                recvIntervals[recvLastIdx] = [s, e, bt]
            if p in pDrop:
                pDrop[p] -= b

print(pDrop)
            
                

sendIntervals = np.array(sendIntervals)
sendThr = sendIntervals[:, 2] / (sendIntervals[:, 1] - sendIntervals[:, 0])

recvIntervals = np.array(recvIntervals)
recvThr = recvIntervals[:, 2] / (recvIntervals[:, 1] - recvIntervals[:, 0])

# print(sendIntervals)

plt.plot(mob, sendThr*8/1024/1024, label='send', marker='o')
plt.plot(mob, recvThr*8/1024/1024, label='recv', marker='x')
plt.title('Throughput vs Euclidean distance')
plt.xlabel('distance')
plt.ylabel('Mbps')
plt.legend()
plt.savefig(ROOT/'a.png')
plt.show()