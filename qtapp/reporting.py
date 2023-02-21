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
import time
import zmq
import multiprocessing as mp
import random
   
class RealtimePlot(QtWidgets.QWidget):
    def __init__(self, data):
        super(RealtimePlot, self).__init__()
        self.data = data

        self.graphWidget = pg.PlotWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.graphWidget)
        self.setLayout(layout)

    def plot(self):
        if len(self.data) > 0:
            which_node = random.choice(list(self.data.values()))
            if len(which_node) > 0:
                data_array = random.choice(list(which_node.values()))

                self.graphWidget.plot(data_array.get_slice, clear=True)

class FSGuiLiveDialog(QtWidgets.QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setWindowTitle('Live')

        self.app = app

        self.data_buffers = {}

        self.plot_widget = RealtimePlot(self.data_buffers)
        # self.plot_widget = RealtimePlot(fsgui.nparray.CircularArray(3000))
        self.layout().addWidget(self.plot_widget)

        self.poller = zmq.Poller()
        self.registered_location_set = set()
        self.location_to_sub = {}
        self.sock_dict = {}

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.__run_update_function)
        self.timer.start(20)
    
    def __run_update_function(self):
        # 20ms deadline.
        t0 = time.time()

        # 6 out of 20 ms is spent plotting.
        self.plot_widget.plot()

        t1 = time.time()
        
        self.__update_publishers()

        t2 = time.time()

        # 0 out of 20 ms is spent polling.
        self.__poll_data()

        t3 = time.time()

        print(f't1: {t1-t0:.3f}, t2: {t2-t1:.3f}, t3: {t3-t2:.3f}')

    def __update_publishers(self):
        app_reporter_map = self.app.get_reporters_map()
        location_set = { l for l in app_reporter_map.values() }

        location_to_node_map = { l: n for n, l in app_reporter_map.items() }
        for l in location_set - self.registered_location_set:
            self.registered_location_set.add(l)
            sub = fsgui.network.UnidirectionalChannelReceiver(l)
            self.location_to_sub[l] = sub
            self.poller.register(sub.sock)
            self.sock_dict[sub.sock] = location_to_node_map[l], sub
            
        for l in self.registered_location_set - location_set:
            self.registered_location_set.remove(l)
            sub = self.location_to_sub.pop(l)
            self.poller.unregister(sub.sock)
            self.sock_dict.pop(sub.sock)
    
    def __poll_data(self):
        # use polling to receive from multiple pubs without blocking in sequence
        results = dict(self.poller.poll(timeout=0))

        for sock in results:
            node_id, sub = self.sock_dict[sock]

            # identify where we to put the data
            node_data_buffers = self.data_buffers.setdefault(node_id, {})

            # may have to receive multiple?
            data = sub.recv()
            while data is not None:
                for key, value in data.items():
                    node_data_buffers.setdefault(key, fsgui.nparray.CircularArray(3000)).place(value)
                
                data = sub.recv(timeout=0)
            

