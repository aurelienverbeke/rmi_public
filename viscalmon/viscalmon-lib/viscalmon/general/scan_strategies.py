# A simple script to show Jabbeke and Wideumont scan strategies
# See also wradlib.vis.plot_scan_strategy



import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure(figsize=(15, 15))
ax_jabbeke, ax_wideumont = fig.subplots(2, 1)

ranges = np.arange(0, 300, 0.1)
elevations = [25.0,13.0,9.0,6.5,4.8,3.8,3.4,2.9,2.2,2.1,1.5,1.2,0.9,0.5,0.3]
beamwidth = 0.97

for (ax, alt, radar) in zip([ax_jabbeke, ax_wideumont], [0.05, 0.585], ["Jabbeke", "Wideumont"]):
    for elevation in elevations:
        top = np.square(ranges)/2/6370 + ranges*np.sin((elevation+beamwidth/2)*np.pi/180) + alt
        bottom = np.square(ranges)/2/6370 + ranges*np.sin((elevation-beamwidth/2)*np.pi/180) + alt
        mid = np.square(ranges)/2/6370 + ranges*np.sin(elevation*np.pi/180) + alt
        ax.plot(ranges, mid, "k")
        ax.fill_between(ranges, bottom, top, alpha=0.7, label=str(elevation)+"°")

        im = plt.imread("radar.png")
        ax.imshow(im, aspect='auto', extent=(-10, 0, alt-1.5, alt), zorder=-1)

        ax.set_ylim([alt-2, 15])
        ax.set_xlim([-12, 305])
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Altitude (km)")
        ax.tick_params(right=True, labelright=True)
        ax.legend(loc="upper left")
        ax.set_title(radar)

plt.show()
