This viewer allows you to display some images created from the archived radar raw scans.

There is two types of images:
- PPIs: to visualize the volume scans ($0.3^\circ$ - $25^\circ$), projected on a map
- "Azimuth-distance": to visualize the vertical/BirdBath scans.
	X axis: gates, the radar is on the left.
	Y axis: azimuths, $0^\circ$ (north) is on the top.

| PPI viewer | Azimuth-distance viewer |
| --- | --- |
| ![[radar_viewer_ppi.png]] | ![[radar_viewer_azidist.png]] |

---

**For the moment, this viewer is user-dependant. It means everyone needs to launch his/her own instance of it and make sure the stored data doesn't use too many space.**

---

>[!warning] Velocity
>Only scans from Z scanning strategy part are displayable.
>Below 4.8°, the scanning strategy is not made to have valid velocity fields.
>Hence, PPIs have absolutely no sense.

>[!info] How does it work ?
>2 main parts :
>- Web viewer
>- Images creation
>
>###### Web viewer
>The web viewer is coded in Python Flask.
>
>It allows to select a time interval, a radar, a moment and an elevation and displays all the available images corresponding to those 4 criteria.
>It's possible to configure the opacity of both map and image layers.
>To display a certain image corresponding to a timestamp, just put your mouse on it (on the right of the screen).
>
>It's also the only way to create new images for other time intervals. You just need to click on the "Images management" button then "Add".
>Here you can select all the images you want to create, and then click "Confirm". (see screenshot below)
>It can take some time and when it's done the page is automatically reloaded.
>**If some moments have not been created, it's probably they aren't archived.**
>
>![[radar_viewer_new_images.png|400]]
>
>###### Images creation
>This Python script is automatically called by the web server when you make a request to add new images.
>
>It first get all the file name, then opens and reads them all, then creates the image in png format.
>The color maps used are stored in the `colormaps.json`. They all come from the Météo-France SERVAL system.
>
>For better performance, the image creation phase is parallelized. The Python variable `MAX_NB_PROCESSES` sets the number of processes running at the same time.

>[!info] Polar to cartesian convertion
>Doviak and Zrnic, *Doppler radar and weather observations*, Second edition, p. 21
>$$z = \sqrt{r^2 + R^2 + 2 r R \sin{(\theta_e)}} - R \tag{2.28b}$$
>$$s = R \arcsin{\left(\frac{r \cos{(\theta_e)}}{R + h}\right)} \tag{2.28c}$$
>Where $R$ is the equivalent radius of the Earth, $\approx \frac{4}{3} \times 6371 \text{km}$ and $\theta_e$ the elevation angle
>
>So $x = s \sin{(\theta_a)}$ and $y = s \cos{(\theta_a)}$ with $\theta_a$ the azimut angle
>
>>%%[!success] Final formula
>>For efficiency and simplicity, we simply take $x = r \sin{(\theta_a)} \cos{(\theta_e)}$ and $y = r \cos{(\theta_a)} \cos{(\theta_e)}$
>>The difference is only $\approx 86 \text{m}$ at $300 \text{km}$%%
>
>For interpolating data on the cartesian grid, we get the coordinates of the polar grid in the cartesian grid (`wradlib.georef.polar.spherical_to_xyz`) and then call an interpolation function (`wradlib.ipol.Nearest` or `scipy.interpolate.griddata`)
>Here we use nearest-neighbor interpolation with `scipy.interpolate.griddata`
>
>At the end, we obtain an image projected in azimuthal equidistant projection centred on radar (proj string: `+proj=aeqd +lat_0=<lat radar> +lon_0=<lon radar> +x_0=0 +y_0=0 +R=6371000 +units=m +no_defs +type=crs`)

>[!example] Files and naming conventions
>Under folder named in environment variable `DIR_PPI` and `DIR_AZI_DIST` (in the container), then folders for each time interval.
>
>Image : `<radar>_<date and time YYYYMMDDHHMM>_<elevation in degrees*10>_<moment in Rainbow format>.png`
>
>Information (`info.csv`) :
>- grouped by radar then moment then elevation then date and time
>- contains the range of the image in km

>[!todo] TODO
>Under images management, add a possibility of deleting or adding a set of images by selecting them in a tree view. The button already exists but does nothing.
>For now, there's just an indication of the disk size occupied by the images and you need to remove it manually in the folder (see container `.env`, variable `DIR_PPI` and `DIR_AZI_DIST`)
>Make a user-independant version, maybe making only temporary images that are deleted after exiting the viewer.
>Add other moments (ET, W at least)
>To improve speed : do it in C/C++?