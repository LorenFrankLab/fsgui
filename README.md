# fsgui
Feedback and stimulation gui for real time experiment control.
This package works with a [specific version](https://gitlab.com/trevortknguyen/trodes-fsgui-fork) of Trodes.

## Installing FSGui locally via pip.

We want to install fsgui along with its dependencies.
After cloning the repository, navigate to the directory that contains `setup.py` and run the command `pip install --editable .` to install locally.
Now you can run `python -m fsgui` to start up fsgui independently of Trodes.

```
# create and activate environment
conda create -n fsgui python=3.10
conda activate fsgui

git clone https://github.com/LorenFrankLab/fsgui
cd fsgui

# install package locally with dependencies
pip install --editable .
```

## Running

`python -m fsgui`

## Documentation

[Full documentation is here.](https://docs.google.com/document/d/1yfo4J65WxpfWlnMLRzXw-R4xlYvEjnC-SLvF4gEMujQ/edit?tab=t.0)

