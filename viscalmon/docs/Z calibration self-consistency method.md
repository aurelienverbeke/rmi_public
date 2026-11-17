>Ryzhkov and Zrnic, Chapter 6 "Data Quality and Measurement Errors", *Radar Polarimetry for Weather Observations*, Springer, 2019, p. 148-151 [doi:10.1007/978-3-030-05093-1](https://doi.org/10.1007/978-3-030-05093-1)

> Gourley et al., "Absolute Calibration of Radar Reflectivity Using Redundancy of the Polarization Observations and Implied Constraints on Drop Shapes", *Journal of Atmospheric and Oceanic Technology*, 2009, volume 26, p. 689–703, [doi:10.1175/2008JTECHA1152.1](https://doi.org/10.1175/2008JTECHA1152.1)

## Theory and relations

>[!note] [Ryzhkov et al., *Calibration Issues of Dual-Polarization Radar Measurements*, 2005](Calibration%20Issues%20of%20Dual-Polarization%20Radar%20Measurements.md)
> $$Z = a + b \, \log{(K_{DP})} + c \, Z_{DR} \tag{1}$$
> With $Z$ and $Z_{DR}$ in dB

>[!note] Goddard et al., *Technique for calibration of meteorological radars using differential phase*, 1994
> $$\frac{K_{DP}}{Z} = f(Z_{DR}) \tag{2}$$
> With $Z$ in $\text{mm}^6 \text{m}^{-3}$

>[!note] Gourley et al., *Absolute Calibration of Radar Reflectivity Using Redundancy of the Polarization Observations and Implied Constraints on Drop Shapes*, 2009
>$f(Z_{DR})$ can be approximated with
> $$f(Z_{DR}) = 10^{-5} \, (a_0 + a_1 Z_{DR} + a_2 Z_{DR}^2 + a_3 Z_{DR}^3) \tag{3}$$

> [!abstract] Values for $a_0$, $a_1$, $a_2$ and $a_3$ in (3)
> 
> | From | Frequency | Temperature (°C) | ZDR range (dB) | $a_0$ | $a_1$ | $a_2$ | $a_3$  |
> | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
> | Ryzhkov and Zrnic (2019) | C - $5.5 \ \text{GHz}$ | 0 – 30 | 0.2 – 2 | 6.7 | -4.42 | 2.16  | -0.404 |
> | Gourley et al. (2009) | C - $5.6 \ \text{GHz}$ | 0 | 0 - 2 | 6.746 | -2.97 | 0.711 | -0.079 | ^parameters-sets
>
> Values obtained with relation^[Brandes et al., "Experiments in rainfall estimation with a polarimetric radar in a subtropical environment", *Journal of Applied Meteorology and Climatology*, 2002, volume 41, p. 674-685, [doi:10.1175/1520-0450(2002)041<0674:EIREWA>2.0.CO;2](https://doi.org/10.1175/1520-0450\(2002\)041<0674:EIREWA>2.0.CO;2)]
> $$r = 0.9951 + 0.02510 D - 0.03644 D^2 + 0.005303 D^3 - 0.0002492 D^4 \tag{BZV}$$ 
>
> > [!quote] Gourley et al. (2009), about $r - D$ relation before
> > The model proposed by BZV and a hybrid model composed of ABL shapes from 0–1.3 mm and then GCB thereafter both led to stable calibration results, with much less variability from ray to ray, that were independent of drop size. [...] Results presented in this study support the notion that there is a unique model that relates drop oblateness to diameter for rain in midlatitudes, and the linear drop shape models are not suitable.
>
> >[!info] Adaptation to a specific radar wavelength / frequency
> > For adapting to radar frequency, Ryzhkov and Zrnic (2019) proposes to divide $f(Z_{DR})$ by $\frac{\lambda_{radar}}{\lambda_{model}} = \frac{f_{model}}{f_{radar}}$
> >
> >We will rather multiply by $\frac{f_{radar}}{f_{model}}$, as floating-point multiplications are faster than divisions


## Method

>[!summary] Conditions
>
> ##### In Ryzhkov and Zrnic (2019)
> 
> - Appropriate range of $Z_{DR}$
> - $\text{SNR} > 25 \text{dB}$
> - $\rho_{HV} > 0.99$
>
> ##### In Gourley et al. (2009), Table 1
> 
> | Problem source | Correction method, threshold, or ray rejection criterion | Implemented ? |
> |---|---|---|
> | Miscalibration in $Z_{DR}$ | Calibrate $Z_{DR}$ using measurements at vertical incidence | ⬅️ We need to get results from $Z_{DR}$ vertical calibration or monitoring |
> | Azimuthal dependence of $Z_{DR}$ due to near-radome interference | Correct $Z_{DR}$ using empirical mask | ⬅️ / ❌ ($Z_{DR}$ bias is the same for all azimuts) |
> | Reduced $Z_H$ due to water-coated radome | Reject entire scan if mean $Z_H$ at vertical incidence from 840 to 2760 m in altitude $> 20~\mathrm{dBZ}$ | ⬅️ |
> | Reduced $Z_H$ and $Z_{DR}$ due to attenuation | $\Delta \Phi_{DP}^{\mathrm{obs}} < 12^\circ$ | ✅ |
> | Mie scattering effects on $Z_H$, $Z_{DR}$, and $\Phi_{DP}^{\mathrm{obs}}$ | Reject ray if a single observation in rain path has $Z_{DR} > 3.5~\mathrm{dB}$ | ✅ |
> | $\Phi_{DP}^{\mathrm{obs}}$ at beginning of rain path $\neq 0^\circ$ | Find initial $\Phi_{DP}^{\mathrm{obs}}$ for each ray by computing mean in 6-km window | ✅ With first 20 gates if they have $\rho_{HV} > 0.98$ |
> | Noisy $\Phi_{DP}^{\mathrm{obs}}$ in light rain | $\Delta \Phi_{DP}^{\mathrm{obs}} > 10^\circ$<br>Rain pathlength $> 15~\mathrm{km}$<br>Smooth $\Phi_{DP}^{\mathrm{obs}}$ and $\Phi_{DP}^{\mathrm{th}}$ in 6-km window | ✅ With $12^\circ$<br>✅<br>✅ But with a 25-bins window (mean of sine and cosine then arctan2) |
> | Nonprecipitating echoes | Reject ray if $> 5\%$ of gates in path were classified as nonprecipitating pixels using fuzzy logic classification algorithm (Gourley et al. 2007 ^[Gourley et al., "A fuzzy logic algorithm for the separation of precipitating from nonprecipitating echoes using polarimetric radar observations", *Journal of Atmospheric and Oceanic Technology*, 2007, volume 24, p. 1439–1451, [doi:10.1175/JTECH2035.1](https://doi.org/10.1175/JTECH2035.1)]) | ✅ ⚠️ Done assuming precipitation echoes have $\rho_{HV} > 0.9$. In the future, could be more efficient to use echoes type data from Rainbow. If there are more than 5% of non-rain echoes we remove the ray, else we just remove the concerned pixels from the ray. |
> | Presence of hail | Reject ray if a single observation in path has $Z_H > 50~\mathrm{dBZ}$ | ✅ |
> | Presence of partially melted or frozen hydrometeors | Range at end of path $< 65~\mathrm{km}$ (or dip in $\rho_{HV}$) | ✅ Just limiting the altitude to $3 \ \mathrm{km}$ |
> 
> Legend : ✅ Done, ⬅️ TODO, ❌ Won't be done
> 
> **In source code, search for `HERE` to see where corrections need to be implemented**
>
> ##### Pre-processing order
> 1. Remove missing pixels where no data available
> 2. Consider rain pixels with $\rho_{HV} \geq 0.98$
> 3. Remove attenuated pixels with $\Phi_{DP} > 12^\circ$
%%> 4. Smooth remaining valid pixels%%
> 4. Limit to $1 \ \mathrm{km}$ in distance and $3 \ \mathrm{km}$ in altitude
> 5. Determine rain paths :
> 	- closest to the radar
> 	- biggest range of consecutive valid pixels
> 	- max $5 \%$ missing / invalid points in path
> 	- min $15 \ \mathrm{km}$ length
> 6. Remove rays where :
> 	- at least one precipitation pixel has $Z > 50 \mathrm{dB}$
> 	- at least one pixel has $Z_{DR} > 3.5 \mathrm{dB}$
> 	- more than $20 \%$ rain pixels with $Z > 30 \mathrm{dB}$
> 	- more than $5 \%$ pixels with $\rho_{HV} < 0.9$ (non-precipitation-pixels)

>[!note] By Gourley et al. (2009)
>For each ray, compare $\Phi_{DP}^{\mathrm{(obs)}}(R)$ and $\Phi_{DP}^{\mathrm{(th)}}(R) = 2 \int_0^R{K_{DP}^\mathrm{(th)} dr} = 2 \int_0^R{Z_{\mathrm{lin}}f(Z_{DR}) dr}$
>With $R \in [0 \; ; R_\mathrm{max}]$ the distance ranges to the radar
>>[!warning] $\Phi_{DP, 0}$
>>$\Phi_{DP}^{\mathrm{(obs)}} \, (R=0)$ must be $0$
>
>>[!question] Differences for biases in $Z$ and $Z_{DR}$ (just informative)
>>$K_{DP}^{\mathrm{(th)}}(Z=20 \text{dBZ}, Z_{DR}=0 \text{dB}) \approx 7.10^{-3} \ \text{deg km}^{-1}$ → $\Phi_{DP}^{\mathrm{(th)}}(100\text{km}) \approx 1.4^\circ$
>>$K_{DP}^{\mathrm{(th)}}(Z=20 \text{dBZ}, Z_{DR}=1 \text{dB}) \approx 4.10^{-3} \ \text{deg km}^{-1}$ → $\Phi_{DP}^{\mathrm{(th)}}(100\text{km}) \approx 0.8^\circ$
>>$K_{DP}^{\mathrm{(th)}}(Z=20 \text{dBZ}, Z_{DR}=2 \text{dB}) \approx 3.10^{-3} \ \text{deg km}^{-1}$ → $\Phi_{DP}^{\mathrm{(th)}}(100\text{km}) \approx 0.6^\circ$
>>$K_{DP}^{\mathrm{(th)}}(Z=19 \text{dBZ}, Z_{DR}=1 \text{dB}) \approx 3.10^{-3} \ \text{deg km}^{-1}$ → $\Phi_{DP}^{\mathrm{(th)}}(100\text{km}) \approx 0.6^\circ$
>>$K_{DP}^{\mathrm{(th)}}(Z=21 \text{dBZ}, Z_{DR}=1 \text{dB}) \approx 5.10^{-3} \ \text{deg km}^{-1}$ → $\Phi_{DP}^{\mathrm{(th)}}(100\text{km}) \approx 1^\circ$

>[!info] Statistics implemented
>We plot mean/median for-each-pixel-difference between estimated and observed smoothed $\Phi_{DP}$ depending on air (*ie* not ground) distance to the radar
>For [both sets of parameters](#^parameters-sets)
>For all elevations $\leq 3^\circ$
>All 5-minutes scans are concatenated

>[!question] Max value for number of points axis (on the right, with blue bars)
>For both single elevations and all elevations together : automatic (totally illogical because not proportional to the number of scans, **needs to be changed**)


## Results

The results are presented for the situations below:
- 2025-05-27 12:25 → 2025-05-27 16:25 for Jabbeke
- 2025-07-06 05:25 → 2025-07-06 10:25 for Wideumont

**These are perfect situations with light stratiform rain above the radar**

| Wideumont | Jabbeke |
| --- | --- |
| ![[wideumont_202507060525_202507061025_z_consistency.png]] | ![[jabbeke_202505271225_202505271615_z_consistency.png]] |

On perfect situations as those ones (light stratiform rain), the difference between estimated and observed differential phase is quite constant along the distance to the radar.
It's quite the same for mean and median, and for both sets of parameters.
But we can still observe a decreasing tendency, which is a lot more visible on different situations with higher reflectivities or smaller rain cells, especially for the lowest elevations.

Then this calibration method seems to be too noisy for the moment. If the reliability isn't improved, it's difficult to use it operationally.