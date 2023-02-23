from PyQt6 import QtWidgets, QtCore, QtGui

import fsgui.application
import fsgui.network
import fsgui.nparray
import qtapp.component
import qtgui
import functools
import qtapp.logging
import fsgui.writer

import traceback
import logging
import graphviz
import threading
import pyqtgraph as pg
import time
import zmq
import multiprocessing as mp
import random
import numpy as np
   
class RealtimePlot(QtWidgets.QWidget):
    def __init__(self, data):
        super(RealtimePlot, self).__init__()
        self.data = data

        self.graphWidget = pg.PlotWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.graphWidget)
        self.setLayout(layout)

    def plot(self):
        self.graphWidget.plot(np.flip(self.data.array), clear=True)

class PlotChoice(QtWidgets.QWidget):
    def __init__(self, app, data_buffers):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())


        self.data_buffers = data_buffers

        self.tuple_map = {}
        self.button_map = {}
        self.widget_map = {}
    
    def update_publishers(self):
        buffer_tuples = {(node_id,key) for node_id in self.data_buffers.keys() for key in self.data_buffers[node_id].keys()}
        widget_tuples = set(self.button_map.keys())

        for tup in buffer_tuples - widget_tuples:
            # add this tup
            widget = QtWidgets.QPushButton(f'Show/hide {tup[1]}')
            widget.clicked.connect(functools.partial(self.__handle_button,tup))
            self.layout().addWidget(widget)
            self.button_map[tup] = widget
    
    def __handle_button(self, tup):
        if tup in self.widget_map:
            widget = self.widget_map.pop(tup)
            self.layout().removeWidget(widget)
        else:
            widget = RealtimePlot(self.data_buffers[tup[0]][tup[1]])
            self.widget_map[tup] = widget
            self.layout().addWidget(widget)

class FSGuiLiveDialog(QtWidgets.QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setWindowTitle('Live')

        self.app = app

        self.data_buffers = {}

        self.plot_choice = PlotChoice(self.app, self.data_buffers)
        self.layout().addWidget(self.plot_choice)

        self.writer = fsgui.writer.HDFWriter(fsgui.writer.generate_filename('fsgui_log'))
        self.buffered_writers = {}

        self.poller = zmq.Poller()
        self.registered_location_set = set()
        self.location_to_sub = {}
        self.sock_dict = {}

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.__run_update_function)
        self.timer.start(20)
    
    def __del__(self):
        print(f'Deleting: {self}')
        for buffered_writer in self.buffered_writers.values():
            buffered_writer.flush()
        self.writer.close()
    
    def __run_update_function(self):
        # 20ms deadline.
        t0 = time.time()

        for widget in self.plot_choice.widget_map.values():
            widget.plot()

        t1 = time.time()
        
        self.__update_publishers()

        t2 = time.time()

        self.__poll_data()

        t3 = time.time()

        self.plot_choice.update_publishers()

        t4 = time.time()

        print(f't1: {t1-t0:.3f}, t2: {t2-t1:.3f}, t3: {t3-t2:.3f}, t4: {t4-t3:.3f}, total: {t4-t0:.3f}')

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
                    self.buffered_writers.setdefault((node_id, key), fsgui.writer.BufferedHDFWriter(node_id, key, self.writer, 256)).append(value)
                
                data = sub.recv(timeout=0)


