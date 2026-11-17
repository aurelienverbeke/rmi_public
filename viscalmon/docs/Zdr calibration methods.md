
>Ryzhkov and Zrnic, Chapter 6 "Data Quality and Measurement Errors", *Radar Polarimetry for Weather Observations*, Springer, 2019, p. 153-155 [doi:10.1007/978-3-030-05093-1](https://doi.org/10.1007/978-3-030-05093-1)

All the results are presented for the situations below:
- 2025-05-27 12:25 → 2025-05-27 16:25 for Jabbeke
- 2025-07-06 05:25 → 2025-07-06 10:25 for Wideumont

**These are perfect situations with light stratiform rain above the radar**

# Vertical / Birdbath

>[!info] Theory
>Seen frow below, rain drops are globally symmetrical (in the sounded volume)
>Hence we should have $Z_H = Z_V \Rightarrow Z_{DR} = 0 \ \text{dB}$

>[!abstract] Method
>**Statistics (mean, median, standard deviation) on the whole dataset, by azimut, by distance, or by $Z$**
>All 5-minute scans are concatenated
>
>To ensure we are in rain : $\rho_{HV} \geq 0.99$
>To ensure we are in *light* rain : $10 \ \text{dBZ} \leq Z \leq 30 \ \text{dBZ}$
>To ensure we are below bright band : $1 \ \text{km} \leq \mathrm{height} \leq 3 \ \text{km}$
>
>>[!bug] TODO
>>Add an automatic filter to ensure we are below the bright band
>>For the moment, the only manual method is to limit the used distances
>>We have the algorithm used by Météo-France, if needed.
>>
>>Or also filter on :
>>- The number of points used for statistics?
>>- The computed standard deviation? ^vertical-todo

>[!success] Results
>| Wideumont | Jabbeke |
>| --- | --- |
>| ![[wideumont_202507060525_202507061025_zdr_vertical.png]] | ![[jabbeke_202505271225_202505271615_zdr_vertical.png]] |
>| $\approx 0.7 \ \text{dB}$ bias | $\approx 0 \ \text{dB}$ bias → perfect |
>| Discretization comes from the different dynamic range | |
>
>It is stable for all azimuts, distances and reflectivities
>
>According to Hubbert et al., *The uncertainty of Zdr calibration*, 2008, as $\sigma \, (Z_{DR}) \approx 0.5\text{dB}$, the type-A uncertainty for 95% accuracy is $2 \sigma \approx 1\text{dB}$

>[!question] Max value for number of points axis (on the right, with blue bars)
>For $Z$-depending statistics : $100,000$ (totally illogical because not proportional to the number of scans, **needs to be changed**)
>For azimuth-depending statistics : $\mathrm{number\_gates} \times \mathrm{number\_scans}$
>For distance-depending statistics : $\mathrm{number\_rays} \times \mathrm{number\_scans}$

# $Z$ to $Z_{DR}$ consistency in light rain

>[!info] Theory
>There are theoretical statistical relations between $Z$ and $Z_{DR}$ in light rain for each 2-dBZ range
>
>For C-band (p. 155, Table 6.3):
>
>| $Z \ (\text{dBZ})$      | 20   | 22   | 24   | 26  | 28   | 30   |
>| -------- | ---- | ---- | ---- | --- | ---- | ---- |
>| $Z_{DR} \ (\text{dB})$ | 0.23 | 0.27 | 0.33 | 0.4 | 0.48 | 0.56 |

>[!abstract] Method
>**Get statistical relations (mean, median) between $Z$ and $Z_{DR}$** for groups of 2-dB $Z$ ranges between $14 \ \text{dBZ}$ and $30 \ \text{dBZ}$ (theoretical values are only given between $20 \ \text{dBZ}$ and $30 \ \text{dBZ}$ but it's still useful to see what it looks like for lower $Z$ values) and compare them to the theoretical values
>All 5-minute scans are concatenated
>
>To ensure we are in rain : $\rho_{HV} \geq 0.99$
>To ensure we are in *light* rain : $14 \ \text{dBZ} \leq Z \leq 30 \ \text{dBZ}$
>To ensure the data is not too attenuated : $\Phi_{DP} \leq 10^{\circ}$
>To remove the noise around the radar : $\mathrm{distance} \geq 2 \ \text{km}$
>To stay below the bright band : $\mathrm{height} \leq 3 \ \text{km}$
>
>>[!bug] TODO
>>[Same as for vertical scans](#^vertical-todo)

>[!success] Results
>| Wideumont | Jabbeke |
>| --- | --- |
>| ![[wideumont_202507060525_202507061025_zdr_consistency.png]] | ![[jabbeke_202505271225_202505271615_zdr_consistency.png]] |
>| $\approx 0.7 \ \text{dB}$ bias | $\approx 0-0.3 \ \text{dB}$ bias |
>| | Increasing bias with decreasing elevation → caused by the elevation rotary joint. Some rotary joints have this problem, it's neither fixable nor predictable. |
>The bias found here are the same as for BirdBath method, maybe with a $\approx 0.1 \ \text{dB}$ difference that we can consider as a normal statistical error.
>
>In Météo-France they only compare the value at $20 \ \text{dBZ}$ to $0.375 \ \text{dB}$, so with this method the results are still good.
>Knowing that, maybe the theoretical values given in the book are a bit low.

>[!question] Max value for number of points axis (on the right, with blue bars)
>For single elevations : $10,000 \times \mathrm{number\_scans}$
>For all elevations together : $100,000 \times \mathrm{number\_scans}$