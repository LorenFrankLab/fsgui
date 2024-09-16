import sys
import h5py
import numpy as np
from datetime import datetime
import tzlocal

"""
Run this program by typing under fsgui environment: python logTime.py xxx_fsgui_log.h5
written by: Shijie Gu
"""

filename = sys.argv[1]
h5 = h5py.File(filename,'r')
h5keys = list(h5.keys())

process = {}
for i in range(len(h5keys)):
    dset = h5[h5keys[i]]
    fields = list(dset.keys())
    #print('node',i,fields)
    if fields[0][:3] == 'rip':
        process['rip'] = i
    elif fields[0][:3] == 'OUT':
        process['OUT'] = i
    elif fields[0][:3] == 'spe':
        process['spe'] = i

## get trigger timestamp
processID = process['OUT']
dset = h5[h5keys[processID]]

timestamps = np.array(dset['OUTPUT_timestamp'])
(t0, t1) = (timestamps[0], timestamps[-1])

## convert to PST. Unclear with day-light saving will do this
local_timezone = tzlocal.get_localzone() #this may help day-light saving

t0_datetime = datetime.fromtimestamp(t0, local_timezone)
t0_datetime = t0_datetime.strftime('%Y-%m-%d %H:%M:%S')

t1_datetime = datetime.fromtimestamp(t1, local_timezone)
t1_datetime = t1_datetime.strftime('%Y-%m-%d %H:%M:%S')

## print
print(f"Starting time {t0_datetime} and ending time {t1_datetime}")