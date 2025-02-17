![alt text](/images/doc_00.png "Logo")

# tofo - Target of Opportunity Tool (aka Toot!)

Simple target of opportunity tool used to plan exoplanet and photometry sessions.

The tool can be used to see what exoplanet transits will be visible on any particular day and then what other targets (variable stars) will be visible at the same time in the field of view and if they will be having any interesting events. This specifically looks for eclipse-type events.

All fields of view with targets of opportunity can be saves as skyfield images and as text data sets.

## Installation

This too has been tested with python 3.13 under *conda* and outside, on both windows and linux. It is recommended that you create a `venv` and install the tool in there. First you will need to install all packages, preferably using `requirements.txt`, and then you can just run `python tofo.py` however you will also need to set up your observatory by copying `observatory_example.yaml` to `observatory.yaml` and editing it. You may also want to provide your own horizon file by copying `horizon_example.csv` and adjusting `observatory.yaml` accordingly. See [usage](doc/usage.md) for more detailed usage example and [observatory specification](doc/observatory.md) for more details about how to define your observatory.

A possible `pip` session (on linux) may look something like this but of course YMMV:

```
> python -m venv .venv_tofo
> source .venv_tofo\bin\activate
> pip install -r requirements.txt
> cp observatory_example.yaml observatory.yaml
> vi observatory.yaml
[edit your file]
> cp horizon_example.csv horizon.csv
> vi horizon.csv
[edit your file]
> python tofo.py
[profit]
```

## Usage

You can load targets from a file, see eg `targets.csv`, or you can add them manually by adding a row and typing in the object name in the `name` column. It is probably easier to just load ExoClock targets using the `Load Exoclock Targets` menu option.

Once you have a list of targets you cen see if they are visible or not by looking at the table (object that are not visible are grayed out) or by looking at the plot at the bottom. If the plotted paths are within the horizon (ie inside the horizon polygon) they will be visible. If you want to know what path belongs to what target just click on it and the name will be shown in the status bar.

To see targets of opportunity for a specific target, double click on the row number and a new window will open. It may take some time as it will be downloading sky image and other interesting object in the background. Once loaded, this screen is not interactive but you can save the image and the data by clicking on the `save` button.

For more detailed instructions have a look at the [usage example](doc/usage.md).

For information about the `observatory.yaml` have a look at the [specification](doc/observatory.md) which also includes information about the horizon file.

Enjoy!

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests (if any) as appropriate.

## General Caveat

The code is not ideally structured for an UI applications. UI uses [wxpython](https://www.wxpython.org/) (which is hardly nice) while the rest evolved from a number of Jupyter notebooks. Data sources etc have been been copied from some other personal projects so they, again, are not ideal. Use of HDF5 is also incidental and, potentially, something like SQLite may have be a better choice. Pickling too could have worked but the spring is coming soon and the pickling season is long behind us. As already stated, the tool organically evolved and is not the best design by a long shot.

## License

[MIT](https://choosealicense.com/licenses/mit/)
