>[!info] Methods source
>All the methods, algorithms and interpretation come from Météo-France, except for the Ravis offsets.
>If you need more information, you can consult the "Guide Utilisateur Monitoring DPOL" (Dual-pol monitoring user guide, only in French unfortunately).
>But all the principal necessary information is translated and explained here.


## Initial $\Phi_{DP}$ offset : $\Phi_{DP, 0}$

#### Statistics

For each scan and each azimuth, compute mean $\Phi_{DP}$ on the first 10 precipitation ($\rho_{HV} \geq 0.99$) gates. The mean $\Phi_{DP}$ value can be flagged as invalid if there are not enough pixels.

For each elevation (and also all together) and each azimuth, compute mean $\Phi_{DP}$ from values above. The associated $\mathrm{number}$ to the azimuth is the number of valid scans used for computing the mean of the concerned azimuth.

From azimuthal $\Phi_{DP}$ means, successively compute curves :
1) Thresholded : keep only azimuths if $\mathrm{number} \geq 1$, else flag as invalid
2) Filtered : moving-window median (15° width) if at least half of the used $\Phi_{DP}$ means are valid
3) Interpolated : interpolate linearly the holes if they don't exceed 30° (**this part is not done as it doesn't change the final result**, but the code is available and commented)

The daily $\Phi_{DP, 0}$ offset is the weighted mean of all azimuthal $\Phi_{DP}$ offsets for the whole-elevations curve.

#### Interpretation

>[!success] Normal behaviour
>$\Phi_{DP, 0}$ should remain stable over the time ($\pm \, 10^\circ$ around the mean).
>Some radars are more stable than others, and we can also observe an annual variation due to the seasons and temperature.
>
>There can be a clear jump after a modification on the radar, especially if some part was replaced or if there was an operation on the wave guides.

>[!failure] Problems
>If $\Phi_{DP, 0}$ constantly diverges (several tens of degrees), a first thing could be to check the wave guides integrity (oxidization, airtightness).
>If $\Phi_{DP, 0}$ really increases or decreases during only warm or cold times, a first thing could be to check all the cables involved in the phase measurement (wave guide output, receiver, GDRX/SP).


## Mean $Z_{DR}$ in rain : $Z_{DR, \text{rain}}$

#### Statistics

For each volumic scan and each azimuth, compute median $Z_{DR}$ with following filters :
- Bright band : $\mathrm{height} \leq 3 \ \text{km}$
- Radar noise : $\mathrm{distance} \geq 1 \ \text{km}$
- Attenuation : $\mathrm{distance} \leq 50 \ \text{km}$ and $\Phi_{DP} \leq 10^\circ$
- Light rain : $15 \ \text{dBZ} \leq Z \leq 25 \ \text{dBZ}$ and $\rho_{HV} \geq 0.99$

For each elevation (and also all together) and each azimuth, compute mean $Z_{DR}$ from median $Z_{DR}$ values above (from each scan). The associated $\mathrm{number}$ to the azimuth is the number of valid pixels used for computing the mean of the concerned azimuth.

From azimuthal $Z_{DR}$ means, successively compute curves :
1) Thresholded : keep only azimuths if $\mathrm{number} \geq 100$, else flag as invalid
2) Filtered : moving-window median (15° width) if at least half of the used $Z_{DR}$ means are valid
3) Interpolated : interpolate linearly the holes if they don't exceed 30° (**this part is not done as it doesn't change the final result**, but the code is available and commented)

The daily $Z_{DR, \text{rain}}$ value is the weighted mean of all the azimuthal $Z_{DR}$ means for the whole-elevations curve.

#### Interpretation

>[!success] Normal behaviour
>$Z_{DR, \text{rain}}$ should remain stable over the time ($\pm \, 0.5 \ \text{dB}$ around the mean).
>It's way less stable than $\Phi_{DP, 0}$, so we should allow some days to be above $\pm \, 0.5 \ \text{dB}$ around the mean without worrying.
>Some radars are more stable than others, and we can also observe an annual variation due to the seasons and temperature. In summer for example, statistics can be disrupted by clear air.
>If $Z_{DR, \text{rain}}$ lightly constantly diverges ($\approx \pm \, 0.3 \ \text{dB}$ per year for example), that's not a problem.
>
>There can be a clear jump after a modification on the radar, especially if it was on the receiver part.

>[!failure] Problems
>If $Z_{DR, \text{rain}}$ quickly diverges ($\approx \pm \, 1 \ \text{dB}$ on some months)
>If $Z_{DR, \text{rain}}$ has really small or high isolated values : check if PPIs look good, else it could be a calibration issue or a failure in the receiver part


## Vertical $Z_{DR}$ bias : $Z_{DR, 90}$

#### Statistics

For each vertical scan, take the median $Z_{DR}$ and the number of the pixels with :
- $10 \ \text{dBZ} \leq Z \leq 30 \ \text{dBZ}$
- $1 \ \text{km} \text{ to the radar} \leq \mathrm{height} \leq 3 \ \text{km altitude}$
- $\rho_{HV} \geq 0.99$ if available

The daily vertical $Z_{DR}$ bias is took as the weighted mean of all computed medians

#### Interpretation

>[!success] Normal behaviour
>It should remain stable at $\approx [-0.5 \ \text{dB} \ ; 0.5 \ \text{dB}]$.
>As for $Z_{DR, \text{rain}}$, there can be a clear jump if a receiver part is changed (which will be the same as for $Z_{DR, \text{rain}}$), and we should allow some points above the limits.
>Long-term evolution of $Z_{DR, 90}$ should follow the one of $Z_{DR, \text{rain}}$ with an approximative gap of $0.3 \ \text{dB}$. This can be more if $Z_{DR, \text{rain}}$ is not the same for all elevations (rotary joint problem).

>[!failure] Problems
>If $Z_{DR, 90}$ quickly diverges (in either positive or negative high values), it's maybe that the TR limiter is defective.
>Also same vigilance points as for $Z_{DR, \text{rain}}$.


## Mean $Z_{DR}$ on first 10 rings around the radar : $Z_{DR, \text{rings}, i}$

#### Statistics

For each scan, it computes the mean of all $Z_{DR}$ in the first 10 1km-long rings.
The daily $Z_{DR, \text{rings}, i}$ is took as the mean of all the $Z_{DR}$ means for the corresponding ring.

Hence, it is a very raw indicator which is useful for hardware monitoring.

$i \in \textlbrackdbl 1 ; 10 \textrbrackdbl$
Ring $i$ has gates whose center is in $[ i-1 \, ; i [$ km

#### Interpretation

>[!success] Normal behaviour
>The first rings can be very noisy due to the proximity to the radar and the TR limiters.
>But on the last (min. 5) rings, $Z_{DR, \text{rings}, i}$ should remain stable.
>In the case of a maintenance operation on the radar, the jump should be the same that is observed on $Z_{DR, 90}$ and $Z_{DR, \text{rain}}$.
>There is often an annual cycle with scattered points in summer due to clear air.

>[!failure] Problems
>Same vigilance points as for $Z_{DR, \text{rain}}$ or $Z_{DR, 90}$.
>
>If a $Z_{DR, \text{rings}, i}$ begins to diverge, then the ones of the next rings, it's probably that a TR limiter is aging:
>The role of a TR limiter is to protect the receiver from the wave sent by the magnetron. The receiver is a very sensitive part which would instantly die if directly exposed to the wave.
>It is like a door which quickly closes and opens at each emission. There is one on each (H and V) channel.
>When it ages, the "door" takes more time to reopen and the received signal is more attenuated.
>Considering both TR limiters don't age at the same time, we can observe this aging on the reflectivity moment.
>Indeed, as $Z_{DR} = Z_H - Z_V$, if $Z_{DR}$ is increasing, the V channel TR limiter is aging, whereas if  $Z_{DR}$ is decreasing, the H channel TR limiter is aging.


## Ravis offsets

#### Statistics

$ZDR_{OFF}$ and $\Phi_{DP}^{OFF}$ are given in the Rainbow scans output files for each sweep.

So we simply take the mean of the offsets for each pulse width if the difference between min and max values doesn't exceed:
- $0.1 \ \text{dB}$ for $Z_{DR}$
- $5^\circ$ for $\Phi_{DP}$

#### Interpretation

This offset is not well documented. Hence we don't know:
- if it corresponds to the total offset, or the 
- if it is applied in the files

## Grafana visualization

All the indicators above are plotted in a Grafana instance. Each radar has its own dashboard and there is a main page that offers an overview on all the radars.

#### Main page

![[grafana_overview.png|1000]]

The main page offers an overview on all the radars. It displays the $Z_{DR,90}$ indicator with the following color scheme :
- $|Z_{DR,90}| < 0.5\text{ dB}$ : green
- $|Z_{DR,90}| < 1\text{ dB}$ : orange
- $|Z_{DR,90}| < 5\text{ dB}$ : red
- $|Z_{DR,90}| > 5\text{ dB}$ : dark red

By clicking on one radar, you can access its complete dashboard.

#### Individual radar page

![[grafana_jabbeke.png|1000]]

On all the plots (apart from Ravis offsets), only the days with more than 10,000 measures are plotted.

No color scheme is set.

By hovering the $i$ on the top-lefts of the plots, you can have a short description of the plot.