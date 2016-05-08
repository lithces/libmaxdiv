import sys
sys.path.append('..')

import numpy as np
import matplotlib.pyplot as plt
import datasets


# Load some time series with seasonal patterns
ids = ['real_3', 'real_9', 'real_12', 'real_13', 'real_14', 'real_15', 'real_17', 'real_18',
       'real_21', 'real_24', 'real_26', 'real_27', 'real_28', 'real_29',
       'real_30', 'real_34', 'real_36', 'real_38', 'real_39', 'real_44', 'real_46', 'real_47', 'real_49',
       'real_50', 'real_51', 'real_52', 'real_54', 'real_55', 'real_56', 'real_57', 'real_60', 'real_65']
gt_period = 24 # our data has a true period of 24 hours
data = { func['id']: func for func in datasets.loadYahooDataset(subset = 'real')['A1Benchmark'] if func['id'] in ids }


def periods2time(periods, n):
    times = float(n) / periods
    return ['{:.0f}h'.format(t) if t <= 48 else '{:.1f}d'.format(t / 24.0) for t in times]


# De-seasonalization by SVD
print('-- SVD --')
minSVDLen = 1420
numLongFuncs = sum(1 for func in data.values() if func['ts'].shape[1] >= minSVDLen)
# Build model matrix
mm = np.ndarray((numLongFuncs, minSVDLen))
row = 0
rowAssoc = {}
for id, func in data.items():
    if func['ts'].shape[1] >= minSVDLen:
        mm[row,:] = func['ts'][0,:minSVDLen]
        rowAssoc[id] = row
        row += 1
# Perform SVD
mm_u, mm_s, mm_vt = np.linalg.svd(mm, full_matrices = False)
# Plot first right singular vectors
fig = plt.figure()
for i in range(6):
    ax = fig.add_subplot(3, 2, i + 1, title = '{}. right-singular vector for singular value {}'.format(i+1, mm_s[i]))
    ax.plot(mm_vt[i,:])
    freq = np.fft.fft(mm_vt[i,:])
    ps = (freq * freq.conj()).real
    period = ps[1:(len(ps)//2)+1].argmax() + 1
    print('Period of {}. right singular vector: {} -> {}'.format(i+1, period, float(minSVDLen) / period))
plt.show()
# Remove some leading singular values
rsRem = int(raw_input('Enter number of right-singular vectors to remove: '))
mm_s[:rsRem] = 0.0
mm_norm = mm_u.dot(np.diag(mm_s).dot(mm_vt))


# De-seasonalization by DFT and Hourly Z Score
print('-- DFT & Hourly Z Score --')
for id in ids:

    # Search non-trivial peak in power-spectrum
    func = data[id]['ts'].ravel()
    freq = np.fft.fft(func)
    ps = (freq * freq.conj()).real
    ps[0] = 0
    th = np.mean(ps) + 3 * np.std(ps)
    period = (ps > th)
    period[0:7] = False
    period[-6:] = False
    period_ind = np.where(period)[0]
    print('{}: period = {} -> {}'.format(id, period_ind[:len(period_ind)//2], periods2time(period_ind[:len(period_ind)//2], len(func))))
    
    # Remove seasonal frequency and reconstruct deseasonalized time series
    freq[period] = 0
    norm_func_dft = np.fft.ifft(freq).real
    
    # Normalize each hour separately by Hourly Z Score
    norm_func_z = func.copy()
    for h in range(gt_period):
        hourly_values = func[h::gt_period]
        norm_func_z[h::gt_period] -= np.mean(hourly_values)
        norm_func_z[h::gt_period] /= np.std(hourly_values)
    
    # Plot
    funcs = [(func, 'Original Time Series'), (ps, 'Power Spectrum'), (norm_func_dft, 'De-seasonalized by DFT'), (norm_func_z, 'De-seasonalized by Hourly Z Score')]
    if id in rowAssoc:
        funcs.append((mm_norm[rowAssoc[id],:].T, 'De-seasonalized by SVD'))
    fig = plt.figure()
    fig.canvas.set_window_title('De-seasonalization of {}'.format(id))
    for row, (f, title) in enumerate(funcs):
        ax = fig.add_subplot(len(funcs), 1, row + 1, title = title)
        ax.plot(f)
        if row == 1:
            ax.plot([0, len(func)-1], [th, th], '--r')
            ax.plot(period_ind, ps[period], 'r.')
    plt.show()
