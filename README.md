# OTlogging

Repository with code to run an OpenTrons protocol simulation and logging its results,
and to parse the text output from the standard `opentrons_simulate`

Installation and instructions
------------

This repo provides two methods for logging the robot's actions.
It relies on the OpenTrons API being installed, and works in the conda environment where the OpenTrons API is installed.

### Installation

The first step is to install [Anaconda](https://www.anaconda.com/distribution/). Once that is done, to install the OpenTrons API, type in the terminal:
```sh
$ conda env create -n opentrons
# use the following line if the above doesn't work:
# conda create -n opentrons
$ source activate opentrons
$ conda install pip
$ pip install opentrons
```

At this point, you should have a functioning OpenTrons environment and you can proceed to install the scripts in this repo:
```sh
$ source activate opentrons
$ git clone https://github.com/luigiferiani/OTlogging.git
$ cd OTlogging
$ pip install -e .
```


### A wrapper for opentrons_simulate

The script `run_opentrons_simulation.py` provides an alternative to the standard `opentrons_simulate`.

It passes a protocol file to `opentrons.simulate.simulate` and captures the output (or "runlog").
This output is a list of dictionaries that represent the commands executed by the robot.
More extensive documentation about this output can be found in Opentrons documentation [here](https://docs.opentrons.com/v1/api.html#opentrons.simulate.simulate).

The runlog is scanned and the summary-level operations are converted into csv format. This will work if your protocol only uses the [Complex Liquid Handling](https://docs.opentrons.com/v1/complex_commands.html) features, but will ignore all actions that were only specified as [Atomic Liquid Handling](https://docs.opentrons.com/v1/atomic_commands.html) actions.
It has been tested on a few protocols and it should work well if the `transfer` method was used.

At the moment, the script ignores, on purpose, any transfer of liquid from the trough into multiple wells.
This will likely change soon though.

#### Usage
```sh
$ source activate opentrons
$ run_opentrons_simulation /path/to/protocol.py -o /path/to/output.csv
# -o is optional, if omitted the output is shown in the terminal
```


### A parser from an already existing text log

The script `parse_robot_log.py` takes instead an existing text file with the printed runlog and parses it to reconstruct the robot's actions.

#### Usage
```sh
$ source activate opentrons
$ parse_robot_log /path/to/runlog.txt -o /path/to/output.csv
# -o is optional, if omitted the output is shown in the terminal
```


Output
------

If the optional flag `-o, --output` is not specified when running the scripts, the output will simply be in the terminal.
If instead the flag is used, the output will be saved in csv format.
Each line represents the transfer of liquid from a well to another, and the columns are, in order:

- source slot (which slot on the robot's deck the source plate is in)
- source well
- destination slot (which slot on the robot's deck the destination plate is in)
- destination well
- liquid volume


Examples
--------


The folder `examples` contains two sets of example files, the runlogs, and the csv outputs obtained with `parse_robot_log.py` and `run_opentrons_simulation.py`.

For example:
- `example_01.py` is a protocol file.
- `runlog_01.txt` contains the robot's output as a text file. It's obtained by running
```sh
$ opentrons_simulate examples/example_01.py >> examples/runlog_01.txt
```
- `output_01_fromwrapper.csv` contains the csv output from running:
```sh
$ python run_opentrons_simulation.py examples/example_01.py -o examples/output_01_fromwrapper.csv
```
- `output_01_fromparse.csv` contains the csv output from running:
```sh
$ python parse_robot_log.py examples/runlog_01.txt -o examples/output_01_fromparser.csv
```
