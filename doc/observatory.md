# `observatory.yaml` File Specification

`observatory.yaml` file is the main source of information for the tool as it provides details about the equipment used and the location of the observatory. The file is also used to select various settings for the tool.

The example file can be seen below. This is the specification for the Palomar observatory and their nice big telescope equipped with the main visible light camera.

![alt text](/images/doc_60.png "Palomar observatory yaml file")

The yaml file has five main sections. Each is described below. Note that SI units are used throughout (apart from temperature which is in Celsius as Celsius makes sense unlike Fahrenheit, Rankine, Rømer, Newton, Delisle, Réaumur, Gas mark, Leiden, Wedgwood etc). If you would like to know more, have a look at [this link](https://xkcd.com/3001/).

## Observatory Section

The `observatory` section collects all the information about the observatory itself. The name, geographical location as well as most common environmental data (temperature, relative humidity and air pressure). The most interesting entry here is the `horizon_file` which has its own [section](horizon.md).

## Telescope and Imaging Sensor Sections

Telescope optics are described in this section (2) which also holds the imaging sensor information (3). All fields should be self explanatory with, possibly, the exception of the `crota1` and `crota2`. These fields describe the rotation of the sensor with respect to normal in the coordinate system. We assume that `tan` is used. `crot n` keywords have been proposed to be replaced since 1983 or thereabouts but they are still used and they are "easy" to use. The easiest way to think of this (which would also be not quite right) is the `crota2` shows the rotation in degrees and then `crota1` will have the same value. See e.g. [this paper](https://www.aanda.org/articles/aa/full/2002/45/aah3859/aah3859.right.html) for the definition and also the proposed replacement etc. Yes that paper is from 2002...

## Observations Section

The `observations` section contains information that is used by the tool to select the initial time it shows, which is set from and to twilight for "today". Type of twilight is set with the `twilight` keywords and valid values are `civil`, `nautical` and `astronomical`. The `minmag` keyword is used to select what is the faintest star we are interested in looking at. For Palomar `16.0` is probably too bright and we could go a few magnitudes down. Finally, when observing exoplanet transits it is necessary to always start before the transit begins and continue recording after the transit ends. Keywords `exo_hours_before` and `exo_hours_after` are used to set these periods.

## Sources Section

Tofo tools uses a number of external data sources to download information about the targets. This section is used to specify which sources are to be used and to provide additional parameters for each source. Additionally this section is also used to specify the name of the cache file. This is done using the `cache_file` keyword. The file name needs to end with the `.hdf5` as that is the format that is used.

Currently supported sources include:

1. ExoClock, specified with the `exoclock` keyword,
2. NASA Exoplanet Archive, specified with the `nasa_exo_archive` keyword,
3. General Catalog of Variable Stars, specified with the `gcvs` keyword, and
4. AAVSO VSX, specified with the `aavso_vsx` keyword

Additional "source" is internally calculated `exo_score` which holds the observing priority and the score for each ExoClock target. See [exoplanet score](exo_score.md) for more information.

Each source target specified an additional keyword `cache_life_days` which specifies how often should the data sources be reloaded. Each time the tool starts it will check how old each cached dataset is and if it is older then the specified lifespan it will be refreshed. This is used so that new additions and updates to ephemeris on ExoClock and NASA Exoplanet Archive are picked up. If the age is specified as `-1` the age is effectively "for ever".

