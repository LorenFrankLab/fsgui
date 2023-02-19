from PyQt6 import QtWidgets, QtCore, QtGui

import fsgui.application
import fsgui.network
import fsgui.nparray
import qtapp.component
import qtgui
import functools
import qtapp.logging

import traceback
import logging
import graphviz
import threading
import pyqtgraph as pg
   
class RealtimePlot(QtWidgets.QWidget):
    def __init__(self, data):
        super(RealtimePlot, self).__init__()
        self.data = data

        self.graphWidget = pg.PlotWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.graphWidget)
        self.setLayout(layout)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(20)

    def plot(self):
        self.graphWidget.plot(self.data.get_slice, clear=True)

class FSGuiLiveWindow(QtWidgets.QWidget):
    def __init__(self, location):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())

        self.location = location

        self.flfp = fsgui.nparray.CircularArray(3000)

        self.plot_widget = RealtimePlot(self.flfp)
        self.layout().addWidget(self.plot_widget)

        # critically we don't use a process because we want it to have the same address space
        self.running = True
        self.thread = threading.Thread(target=self.__run_thread, args=())
        self.thread.start()

    def __run_thread(self):
        """
        It's running on a different thread in the same process.

        Surprisingly, it works. It has an eventual consistency model, which is perfectly fine for us.
        """
        pub = fsgui.network.UnidirectionalChannelReceiver(self.location)

        while self.running:
            data = pub.recv(timeout=50)
            if data is not None:
                flfp = float(data.split(' ')[3])
                self.flfp.place(flfp)
    
    def __del__(self):
        print('deleting')
        self.running = False

if __name__=='__main__':
    location = 'tcp://0.0.0.0:32861'

    qtgui.run_qt_app(functools.partial(
        FSGuiLiveWindow,
        location
    ))
