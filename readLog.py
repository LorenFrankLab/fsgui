import sys
import h5py
import numpy as np

filename = sys.argv[1]
h5 = h5py.File(filename,'r')
h5keys = list(h5.keys())

process = {}
for i in range(len(h5keys)):
    dset = h5[h5keys[i]]
    fields = list(dset.keys())
    print('node',i,fields)
    if fields[0][:3] == 'rip':
        process['rip'] = i
    elif fields[0][:3] == 'OUT':
        process['OUT'] = i
    elif fields[0][:3] == 'spe':
        process['spe'] = i

## print ripple mean and sd estimate
processID = process['rip']
dset = h5[h5keys[processID]]
rip_mean = np.array(dset['rip_mean'])
rip_sd = np.array(dset['rip_sd'])
## check convergence
rip_mean_d = np.diff(rip_mean)
rip_sd_d = np.diff(rip_sd)
if np.mean(rip_mean_d[-100:]) <= 1e-1 and np.mean(rip_sd_d[-100:]) <= 1e-1:
    converge_flag = 1
else:
    converge_flag = 0

if converge_flag:
    print('estimate converged')
    print('ripple mean estimate: ',rip_mean[-1])
    print('ripple sd estimate: ',rip_sd[-1])
else:
    print('estimate DID NOT converge')
    print('last 10 ripple mean estimate: ',rip_mean[-10:])
    print('last 10 ripple sd estimate: ',rip_sd[-10:])

