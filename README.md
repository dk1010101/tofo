# tofo - Target of Opportunity Tool (aka Toot!)

Simple target of opportunity tool used to plan exoplanet and photometry sessions.

The tool can be used to see what exoplanet transits will be visible on any particular day and
then what other targets (variable stars) will be visible at the same time in the field of view
and if they will be having any interesting events. This specifically looks for eclipse-type
events.

All fields of view with targets of opportunity can be saves as skyfield images and as text data
sets.

# Installation

This has been tested with python 3.13 under conda and outside. To make it work you will need to
install all packages in `requirements.txt` and then just `python tofo.py` and you are off but first
you will need to set up your observatory data by copying `observatory_example.yaml` to `observatory.yaml`
and editing it. You may also want to provide your own horizon file by copying `horizon_example.csv` and
adjusting `observatory.yaml` accordingly.

# How to use the tool

You can load targets from a file, see eg `targets.csv`, or you can add them manually by adding a row and
typing in the object name in the `name` column. It is probably easier to just load exoclock targets using
the `Load Exoclock Targets` menu option.

Once you have a list of targets you cen see if they are visible or not by looking at the table (object that
are not visible are grayed out) or by looking at the plot at the bottom. If the plotted paths are within the
horizon (ie inside the horizon polygon) they they are visible. If you want to know what path belongs to
what target just click on it and the name will be shown.

To see targets of opportunity for a specific target double click on the row number and a new window will open.
It may take some time for it to come to life as it will be downloading sky image and AAVSO variable stars
in the background. Once loaded this screen is not really interactive but you can save the image and the data
by clicking on the `save` button.

Enjoy!
