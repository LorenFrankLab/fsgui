# fsgui
Feedback and stimulation gui for real time experiment control

## Running

`python -m fsgui`

## Organization
1. fsgui: just logic, contains no reference to pyqt
2. fsgui.spikegadgets: only place Trodes should ever be mentioned
3. qtapp: QtWidgets that refer to fsgui concepts
4. qtgui: pure QtWidgets components with no reference to fsgui

## Setting up fsgui to work with Trodes

These instructions describe how to set up Trodes to work witih fsgui.

### Installing fsgui locally via pip.

We want to install fsgui along with its dependencies.

After cloning the repository, navigate to the directory that contains `setup.py` and run the command `pip install --editable .` to install locally.
Now you can run `python -m fsgui` to start up fsgui independently of Trodes.

### Creating an executable file that launches fsgui

We want to create an executable that launches fsgui instead of launching it through the Python command.

Navigate to the directory where the Trodes binaries are installed and create a new file with the name `FSGui` without any file extension. Make sure the contents of the file are as follows, substituting the `/path/to/python` with the appropriate value. If you have multiple Python distributions (e.g. you're using Anaconda), get the right path using `which python`.

```
#!/bin/bash
PYTHON=/path/to/python
$PYTHON -m fsgui $@
```

Make sure this file is executable by running `chmod +x ./FSGui`.

### Editing your .trodesconf to launch fsgui when starting your workspace.

Every Trodes configuration has an option to launch modules upon starting your workspace. We want to launch the fsgui module.

Edit the `<ModuleConfiguration>` node to contain one additional tag for `<SingleModuleConfiguration>` specifying to Trodes how to launch the executable we just made.

```
<ModuleConfiguration>
	<SingleModuleConfiguration moduleName="./FSGui" sendNetworkInfo="1" />
</ModuleConfiguration>
```