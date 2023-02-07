# fsgui
Feedback and stimulation gui for real time experiment control

## Running

`python -m fsgui`

## Organization
1. fsgui: just logic, contains no reference to pyqt
2. fsgui.spikegadgets: only place Trodes should ever be mentioned
3. qtapp: QtWidgets that refer to fsgui concepts
4. qtgui: pure QtWidgets components with no reference to fsgui
