>[!info] Goal
>Compare Rainbow QPE, RADQPE2 and rain gauges measurements to evaluate the precision of the rain estimations upon several QPE product types.

>[!abstract] Overview
>This unit runs three types of statistics:
>- QPE-QPE comparisons
>- QPE-rain gauges comparisons
>- QPE-rain gauges time shift estimation

>[!tip] Functioning
>This unit is made of two stages:
>- General algorithms that compute statistics given two data types, two time bounds and some more parameters (see `qpe_qc/qc.py`)
>- Period-fixed algorithms that use the general algorithms and export the results in the database (see `qpe_qc/qc_periodic.py`)

# Input data

Individual radars (Jabbeke, Wideumont, Helcheteren, Avesnois):
- Rainbow5
	- RR
	- Acc 1h/1d **(from 8am l.t. to 8am l.t.)**
- RADQPE2
	- QPE RR
	- QPE Acc 5m/10m/1h/1d **(from midnight to midnight)**
	- QPE MFB Acc 1d **(from midnight to midnight)**

Composite:
- Rainbow5
	- beborder RR
	- becomp RR
	- Acc 10m/1h
- RADQPE 2
	- QPE RR
	- QPE EDK RR
	- QPE MFB RR
	- QPE Acc 5m/10m/1h/1d **(provided every 5 minutes)**
	- QPE EDK Acc 5m/10m/1h/1d **(provided every 5 minutes)**
	- QPE MFB Acc 5m/10m/1h/1d **(provided every 5 minutes)**

Rain gauges :
- ✓ `AWS_10MIN` : RMI automatic network, **validated 2/3 months after the measurements**
- ❌ `AWS_1HOUR` : RMI automatic network, but **redundant with `AWS_10MIN` and no data quality control**
- ❌ `AWS_CLIM_10MIN` : "few precipitation data available, just used to evaluate simple tipping bucket rain gauges of Barani stations"
- ✓ `PRECIPITATION` : RMI mainly manual rain gauges from 8am l.t. to 8am l.t., **validated 2/3 months after the measurements**
- ✓ `HIC_PRECIP_5MIN` : HIC network, **validated 2/3 days after the measurements**
- ✓ `SETHY_PRECIP_5MIN` : SPW-MI network, **validated 2/3 days after the measurements**
- ✓ `SETHY_PRECIP` : SPW-MI network, 1h data, redundant with `SETHY_PRECIP_5MIN`
- ✓ `VMM_PRECIP_5MIN` : VMM, **validated 2/3 days after the measurements**
- ~ `VMM_PRECIP_10MIN` : VMM, **older data, not validated**

# General algorithm 1: Temporal shift

In `qpe_qc/qc.py:g_r_synchronization()`.

The goal here is to measure the mean temporal shift between QPE estimations and rain gauges measurements.
It is made for each radar-gauge couple and can averaged between all rain gauges of several networks.

This type of comparison can be led with QPEs that don't have the same time base as the rain guages. However, only the rain gauges measurements can be summed to match the radar type time base.

> [!example] Example
> - 10 min rain gauges with 10 min QPE $\rightarrow$ OK
> - 10 min rain gauges with 1 hour QPE $\rightarrow$ OK
> - 1 hour rain gauges with 10 min QPE $\rightarrow$ wrong

### Method

We can measure it by cross-correlating both signals during a period.

> [!note] Theoretical algorithm
> $$ \text{shift} = \Delta t = \underset{\tau}{\text{argmax}} \ (R_{RG} (\tau)) $$
> $$ R_{RG} (\tau) = \sum_{t} R(t+\tau) G(t) = \sum_{t} R(t) G(t-\tau) $$
> If $\Delta t > 0$ QPE is early, if $\Delta t < 0$ QPE is late.

Implemented simplified algorithm:
```
Accumulate rain gauges measurements if necessary
R=[[]]
G=[[]]
For each timestamp where both the rain gauges measurements and the radar matrix are available:
	For each available gauge at this timestamp:
		Search the corresponding pixel of the gauge in the radar matrix
		Extend R[gauge] with the radar estimation
		Extend G[gauge] with the gauge measurement
For each gauge:
	n_g_nonzero=number of non-zero positive rain gauges values
	Oversample linearly with ratio 100
	Cross-correlate both oversampled time series
	Find the peaks that have height>=0.5*max(crosscorrelation)
	If no peak is found:
		shift=argmax(correlation)
	Else:
		If peaks that have prominence>=0.5*max(crosscorrelation) and shift<=3*timebase exist:
			shift=time coordinate of the peak whose shift is the closest to 0
		Else:
			shift=not found
```

Were the time base is the radar one.

# General algorithm 2: Temporal biases

In `qpe_qc/qc.py:compare_r_r()` and `qpe_qc/qc.py:compare_g_r()`.

>[!quote] Source
>Based on Edouard Goudenhoofdt's work

### Computed statistics

2 types of statistical indicators are computed:
- QPE vs QPE
- Rain gauges vs QPE

### Scores

> *Forecast verification: a practitioner’s guide in atmospheric science*, edited by Ian T. Jolliffe and David B. Stephenson, Wiley, 2003, ISBN 0-471-49759-2 

#### Continuous scores

Below, $i$ corresponds to the index of a R-R or G-R geographically corresponding couple.

###### Mean Error

> [!note] Formula
> $$ME = \overline{R_i - G_i}$$

###### Median Error

> [!note] Formula
> $$MedE = \text{med}(R_i - G_i)$$

###### Mean Absolute Error

> [!note] Formula
> $$MAE = \overline{|R_i - G_i|}$$

> [!important] Properties
> We take the absolute value so the negative bias don't compensate the positive ones.

###### Root Mean Square Error

> [!note] Formula
> $$RMSE = \sqrt{\frac{\sum(R_i-G_i)^2}{n}}$$

> [!important] Properties
> More sensitive to big differences than MAE.

###### Weighted error

> [!warning]
> Only available for radar-gauges comparisons, not for radar-radar ones.

> [!note] Formula
> Considering $F_{R-G}(r)$ the distribution function of $R-G$ regarding their contribution to the total observed rain volume $G$.
> $$E_w = F^{-1}_{R-G}(0.5)$$

> [!abstract] Algorithm
> ```
> Sort (G) and (R-G) with the sorting order of (R-G)
> Compute the cumulative sum of G
> Find i such as Gi is half the total $G$ sum.
> Ew=(R-G)i
> ```

>[!question] Indicates
> Median error for half the total observed precipitations $G$.
> It is a median-like error with higher weight for higher observations $G_i$.

###### Correlation

> [!note] Formula
> $$\rho = \text{cor}(R, G) = \frac{\text{cov}(R, G)}{\sigma_R\sigma_G}$$
> We propose calculating $\text{mean}(\rho)$ as:
> $$\text{mean}(\rho) = \frac{\text{mean}(\text{cov}(R, G))}{\sqrt{\text{mean}(\text{var}(R)) \cdot \text{mean}(\text{var}(G))}}$$

> [!important] Properties
> Invariant to mean shift and rescaling.
> No need to remove any bias previous **linear** bias correction.

>[!question] Indicates
> A linear relation between both observations and estimations.
> $\rho = 1$ indicates full skill, $\rho = -1$ full inverted skill and $\rho = 0$ no skill

###### Total precipitation bias

> [!note] Formula
> $$B_t = \frac{\sum R_i}{\sum G_i}$$

###### Mean bias

> [!note] Formula
> $$B_{mean} = \overline{\left(\frac{R_i}{G_i}\right)}$$

###### Median bias

> [!note] Formula
> $$B_{med} = \text{med}\left(\frac{R_i}{G_i}\right)$$

###### Weighted bias

> [!warning]
> Only available for rain gauges vs radar comparisons, not for radar-radar ones.

> [!note] Formula
> Considering $F_{\frac{R}{G}}(r)$ the distribution function of $\frac{R}{G}$ regarding their contribution to the total observed rain volume $G$.
> $$B_w = F^{-1}_{\frac{R}{G}}(0.5)$$

> [!abstract] Algorithm
> ```
> Sort (G) and (R/G) with the sorting order of (R/G)
> Compute the cumulative sum of G
> Find i such as Gi is half the total $G$ sum.
> Bw=(R/G)i
> ```

>[!question] Indicates
> Median bias for half the total observed precipitations $G$.
> It is a median-like bias with higher weight for higher observations $G_i$.

###### Scatter score

> Urs Germann, Gianmarco Galli, Marco Boscacci and Martin Bolliger, "Radar precipitation measurement in a mountainous region", *Quarterly Journal of the Royal Meteorological Society*, Volume 132, 2006, Pages 1669-1692, https://doi.org/10.1256/qj.05.190

> [!warning]
> Only available for rain gauges vs radar comparisons, not for radar-radar ones.

> [!note] Formula
> Considering $F_{\frac{R}{G}}(r)$ the distribution function of $\frac{R}{G}$ regarding their contribution to the total observed rain volume $G$.
> $$SCS = F^{-1}_{\frac{R}{G}}(0.83) - F^{-1}_{\frac{R}{G}}(0.17)$$

> [!abstract] Algorithm
> ```
> Sort (G) and (R/G) with the sorting order of (R/G)
> Compute the cumulative sum of G
> Find i (resp. j) such as Gi (resp. Gj) is 83% (resp. 17%) the total $G$ sum
> Bw=(R/G)i-(R/G)j
> ```

>[!question] Indicates
> Spread of the errors contributing to 66% to the rain volume $G$. 

###### Ratio of pairs within 1dB

> [!note] Formula
> $$F_{1dB} = \frac{\sum \delta_i}{n}$$
> $$ \delta_i =
> 	\begin{cases}
> 		1 \quad \text{if} \quad -1dB \leq 10 \log_{10} \left( \frac{R_i}{G_i} \right) \leq 1dB \\
> 		0 \quad \text{otherwise}
> 	\end{cases}
> $$

>[!question] Indicates
> Ratio of pairs estimated as "good" if we consider a max ratio of **1.25**

###### Ratio of pairs within 2dB

> [!note] Formula
> $$F_{2dB} = \frac{\sum \delta_i}{n}$$
> $$ \delta_i =
> 	\begin{cases}
> 		1 \quad \text{if} \quad -2dB \leq 10 \log_{10} \left( \frac{R_i}{G_i} \right) \leq 2dB \\
> 		0 \quad \text{otherwise}
> 	\end{cases}
> $$

>[!question] Indicates
> Ratio of pairs estimated as "good" if we consider a max ratio of **1.6**

###### Nash-Sutcliffe model efficiency coefficient

> [!failure] Not implemented for the moment

> [!note] Formula
> $$NSE = 1 - \frac{MSE}{\text{var}(G)}$$

>[!question] Indicates
> $NSE = 1$ : full skill.
> $NSE = 0$ : no skill, the model has same skills as a simple mean in terms of the sum of the squared error.
> $NSE < 0$ : the observed mean is a better predictor than the model.

###### Kling–Gupta efficiency

> [!failure] Not implemented for the moment

> Hoshin V. Gupta, Harald Kling, Koray K. Yilmaz, Guillermo F. Martinez, "Decomposition of the mean squared error and NSE performance criteria: Implications for improving hydrological modelling", *Journal of Hydrology*, Volume 377, Issues 1–2, 2009, Pages 80-91, https://doi.org/10.1016/j.jhydrol.2009.08.003

> Harald Kling, Martin Fuchs, Maria Paulin, "Runoff conditions in the upper Danube basin under an ensemble of climate change scenarios", *Journal of Hydrology*, Volumes 424–425, 2012, Pages 264-277, https://doi.org/10.1016/j.jhydrol.2012.01.011

> [!note] Formula
> $$KGE = 1 - \sqrt{(\rho-1)^2 + \left(\frac{\overline{R}}{\overline{G}}-1\right)^2 + \left(\frac{\sigma_R}{\sigma_G}-1\right)^2}$$

#### Binary scores

> [!failure] Not implemented for the moment

###### Probability of detection

> [!note] Formula
> $$POD = \frac{hits}{hits + misses}$$

###### False alarm ratio

> [!note] Formula
> $$FAR = \frac{false \ alarms}{hits + false \ alarms}$$

###### Equitable threat score

> [!note] Formula
> $$ETS = \frac{hits - hits_{random}}{hits + misses + false \ alarms - hits_{random}}$$ $$hits_{random} = \frac{(hits + misses)(hits + false \ alarms)}{total}$$

###### Peirce skill score

> [!note] Formula
> $$PSS = POD - POFD = \frac{hits}{hits + misses} - \frac{false \ alarms}{false \ alarms + correction \ negatives}$$

### Events thresholds

The statistics can be computed for several events thresholds, in mm/h.

When setting a threshold, only the compared couples for which the precipitation rate exceeds or equals the threshold are kept.
For radar-radar comparisons: the threshold is compared to the maximum value of both corresponding pixels. Hence, only one of both pixels is required to exceed the threshold to be used in the statitstics computation.
For radar-gauges comparisons: the threshold is only compared to the rain gauge value. Hence, the rain gauge measurement must exceed the threshold for the radar-gauge couple to be used in the statistics computation.

### QPE-QPE comparisons

This type of comparison is made to be led with QPEs that have the same time base: RR and RR, 10 min and 10 min, 1 day and 1 day...

Simplified algorithm:
```
R1_pixels = []
R2_pixels = []
For each timestamp where both radar matrixes are available:
	Search the corresponding pixels in both matrixes
	Extend R1_pixels and R2_pixels with those pixels
Compute the statistics for all the given thresholds
```

### QPE-gauges comparisons

This type of comparison can be led with QPEs that don't the same time base. However, only the rain gauges measurements can be summed to match the radar type time base.

> [!example] Example
> - 10 min rain gauges with 10 min QPE $\rightarrow$ OK
> - 10 min rain gauges with 1 hour QPE $\rightarrow$ OK
> - 1 hour rain gauges with 10 min QPE $\rightarrow$ wrong

Simplified algorithm:
```
Get rain gauges and radar data
Accumulate rain gauges measurements if necessary
R=[[]]
G=[[]]
For each timestamp where both rain gauges measurements and radar matrix are available:
	For each available gauge at this timestamp:
		Search the corresponding pixel of the gauge in the radar matrix
		Extend R[gauge] with the radar estimation
		Extend G[gauge] with the gauge measurement
Compute the statistics for each gauge for all the thresholds
```

# Period-fixed algorithms

In `qpe_qc/qc_periodic.py`.

**Daily radar-gauges time shift**

**Daily mean radar-gauges time shift**

The average on all rain gauges is performed by taking the weighted spatial mean of the individual time shifts were the weight is the number of per-gauge non-zero rain-gauges measurements.

**Daily bias between QPE and QPE**
For the 1-day accumulations valid between 8am l.t. and 8am l.t., the daily indicators corresponds to period \[date at 8am l.t. -> (date+1) at 8am l.t.\].

**Monthly bias between QPE and QPE**
As gathering radar matrixes on one month would consume too much memory, the monthly bias is calculated as the mean of the daily biases, weighted with the daily number of couples used to compute the daily biases.

**Daily bias between rain gauges and QPE**
For the 1-day accumulations valid between 8am l.t. and 8am l.t., the daily indicators corresponds to period \[date at 8am l.t. -> (date+1) at 8am l.t.\].

**Daily mean bias between rain gauges and QPE**
The average on all rain gauges is performed by taking the weighted spatial mean sof the individual statistics were the weight is the number of per-gauge non-zero rain-gauges measurements.
For the 1-day accumulations valid between 8am l.t. and 8am l.t., the daily indicators corresponds to period \[date at 8am l.t. -> (date+1) at 8am l.t.\].

**Monthly bias between rain gauges and QPE**

Same as for *Daily bias between rain gauges and QPE*, during a month instead of a day.

**Monthly mean bias between rain gauges and QPE**

Same as for *Daily mean bias between rain gauges and QPE*, during a month instead of a day.

# Operationally running comparisons

### Events thresholds

We choose three types of events :
- $\geq 0.2 \text{ mm/h}$
- $\geq 1 \text{ mm/h}$
- $\geq 5 \text{ mm/h}$

### Daily radar-gauges time shift

- Single radars: Jabbeke, Wideumont, Helchteren, Avesnois
- Composites
 <br>
- Rainfall rate and 5-min accumulations
 vs
- HIC, SPW and VMM 5-min rain measurements

### Daily bias between QPE and QPE

- Single radars: Jabbeke, Wideumont, Helchteren, Avesnois
- Composite
 <br>
- Rainfall rates and all accumulations

### Monthly bias between QPE and QPE

- Single radars: Jabbeke, Wideumont, Helchteren, Avesnois
- Composite
 <br>
- Rainfall rates and all accumulations

### Daily (mean) bias between rain gauges and QPE

- Single radars: Jabbeke, Wideumont, Helchteren, Avesnois
- Composite
 <br>
- All accumulations
 <br>
- HIC, SPW and VMM 5 min rain measurements

### Monthly (mean) bias between rain gauges and QPE

- Single radars: Jabbeke, Wideumont, Helchteren, Avesnois
- Composite
 <br>
- All accumulations
 <br>
- HIC, SPW and VMM 5 min rain measurements for 5 min radar accumulations
- RMI 10 min rain measurements for 10 min, 1 hour and 1 day midnight-midnight radar accumulations
- RMI manual daily rain measurements for 1 day 8am l.t.-8am l.t. radar accumulations

# Results and interpretation

### Time shift

![[grafana_daily_shift.png]]

On the top bar, you can find selectors for:
- The QPE type compared to the rain gauges
- The radar concerned (only if the QPE type is not a composite type)
- The rain gauges network compared to the QPE **for the per-gauge map**
- The rain gauges network(s) compared to the QPE **for the daily mean**
- The minimum availability (ratio of necessary gauge-radar couples, in %, compared to the theoretical number if all the 5-min data for radar and rain gauges were available)
- The date for which the map is displayed
- A time selector which sets the bounds of the time series and the date selector

On the main part:
- A time series for the daily weighted means computed and all rain-gauges
- A daily map with per-gauge time shifts

The colors are fixed:
- Green for $\text{abs}(shift)<5 \text{ min}$
- Orange for $5 \text{ min} \leq \text{abs}(shift)<10 \text{ min}$
- Red for $\text{abs}(shift) \geq 10 \text{ min}$

The result is computed and exported in seconds, but automatically displayed in minutes by Grafana.
Since the operational comparions are only made on 5-min data products (accumulations or rainfall rates), we should expect results between -300 seconds / -5 minutes and 300 seconds / 5 minutes.

However, this algorithm gives an **estimation** of the time shift, which is very dependent to:
- The number of daily data available
- The shape of the rain system: stratiform, convective, number of rain events in the day...
A perfect day would contain only one convective and intense event, leading to one peak in the daily time series.

Hence, individual outliers shouldn't be considered instantly as problematic.
It's better to read it visually as a mean and observe if there are any deviations from the 0 horizontal rule.

#### Improvement axis

We could compute time series for each gauge to get a more reliable spatial error field.

### QPE-QPE time series

![[grafana_daily_r_r.png]]

On the top bar, you can find selectors for:
- The first QPE type compared
- The second QPE type compared
- The first radar concerned (only if the first QPE type is not a composite type)
- The second radar concerned (only if the second QPE type is not a composite type)
- The minimum availability (ratio of necessary gauge-radar couples, in %, compared to the theoretical number if all the 5-min data for radar and rain gauges were available)
- The minimum rain rate threshold
- The date for which the map is displayed
- The minimum number of daily couples: only daily statistics observing this condition will be displated
- A time selector which sets the bounds of the time series

On the main part, you can observe all the statistics computed.

The graphs bounds are fixed:
- -10 mm to 10 mm for the difference-based statistics
- -10 dB to 10 dB for the ratio-based statistics
- -1 to 1 for the correlation
- 0 to 1 for the ratio of couple within 1 or 2 dB

As before, individual outliers shouldn't be considered instantly as problematic.
It's better to read it visually as a mean and observe if there are any deviations from the theoretical horizontal rule.

#### Improvement axis

We could compute some kind of a spatial error field.

### QPE-gauges time series

![[grafana_daily_g_r.png]]

On the top bar, you can find selectors for:
- The QPE type compared to the rain gauges
- The radar concerned (only if the QPE type is not a composite type)
- The rain gauges network compared to the QPE **for the per-gauge map**
- The minimum availability (ratio of necessary gauge-radar couples, in %, compared to the theoretical number if all the 5-min data for radar and rain gauges were available)
- The minimum rain rate threshold
- The date for which the maps are displayed
- The minimum number of daily couples: only daily statistics observing this condition will be displated
- The statistics to print on the second map
- A time selector which sets the bounds of the time series and the date selector

On the main part, you can observe all the statistics computed

On the main part:
- All the time series
- A daily map with the per-gauge mean error
- A daily map with a customizable variable

The graphs bounds are fixed:
- -10 mm to 10 mm for the difference-based statistics
- -10 dB to 10 dB for the ratio-based statistics
- -1 to 1 for the correlation
- 0 to 1 for the ratio of couple within 1 or 2 dB

As before, individual outliers shouldn't be considered instantly as problematic.
It's better to read it visually as a mean and observe if there are any deviations from the theoretical horizontal rule.

#### Improvement axis

We could compute some kind of a spatial error field.

# APPENDIX - Statistics reminders : estimators and notations

$$\text{mean}(X) = \mu(X) = \overline{X} = \frac{1}{n} \sum^n_{i=1} X_i$$

$$\text{var}(X) = \text{std}(X)^2 = \sigma^2_X = \frac{1}{n} \sum^n_{i=1} \left(X_i - \overline{X} \right)^2$$

$$\text{cov}(X,Y) = \frac{1}{n-1} \sum^n_{i=1} \left(X_i - \overline{X} \right) \left(Y_i - \overline{Y} \right)$$