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
import pyqtgraph.opengl as gl
import time
import zmq
import multiprocessing as mp
import random
import numpy as np
   
class RealtimePlot(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, data, label):
        super().__init__()
        self.data = data

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setLabel('left', label)
        self.layout().addWidget(self.graphWidget)

        self.plot_item = pg.PlotDataItem()
        self.graphWidget.addItem(self.plot_item)

    def plot(self):
        self.plot_item.setData(np.flip(self.data.array))

class RealtimePlot4D(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, data, label):
        super().__init__()
        self.data = data

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', label)
        self.layout().addWidget(self.plot_widget)

        self.plot_item = pg.ScatterPlotItem()
        self.plot_item.setSymbol('o')  # set the symbol to be a circle
        self.plot_item.setPen(None)  # remove the border around the symbols
        self.plot_widget.addItem(self.plot_item)

    def __transform_range(self, values, source_range, target_range):
        return np.interp(values, source_range, target_range)

    def plot(self):
        data = self.data.get_slice[:, :500]

        sizes = data[2,:]
        sizes = self.__transform_range(sizes, [np.min(sizes), np.max(sizes)], [3, 15])

        colors = data[3,:]
        colors = self.__transform_range(colors, [np.min(colors), np.max(colors)], [0,1])

        self.plot_item.setData(pos=data.T[:,:2], size=sizes, brush=colors)

class GL3DPlot(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, data, label):
        super().__init__()
        self.data = data

        self.plot_widget = gl.GLViewWidget()
        self.layout().addWidget(self.plot_widget)

        self.plot_item = gl.GLScatterPlotItem()
        self.plot_widget.addItem(self.plot_item)

    def __transform_range(self, values, source_range, target_range):
        return np.interp(values, source_range, target_range)

    def plot(self):
        data = self.data.get_slice[:, :500]

        sizes = data[3,:]
        sizes = self.__transform_range(sizes, [np.min(sizes), np.max(sizes)], [3, 15])

        self.plot_item.setData(pos=data.T[:,:3], size=sizes)

class HeatmapWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, data, label):
        super().__init__()
        self.data = data

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', label)
        self.layout().addWidget(self.plot_widget)

        self.plot_item = pg.ImageItem()
        # Set colormap and range for heatmap item
        colormap = pg.colormap.get("CET-L4")
        self.plot_item.setLookupTable(colormap.getLookupTable())
        self.plot_item.setLevels([-3, 3])
        self.plot_widget.addItem(self.plot_item)

    def __transform_range(self, values, source_range, target_range):
        return np.interp(values, source_range, target_range)

    def plot(self):
        data = np.flip(self.data.array.T)
        data = self.__transform_range(data, [np.min(data), np.max(data)], [0, 0.75]) + 0.25


        self.plot_item.setImage(data)

class DistributionPlot(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, data, label):
        super().__init__()
        self.data = data

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setLabel('left', label)
        self.layout().addWidget(self.graphWidget)

        self.plot_item = pg.PlotDataItem()
        self.graphWidget.addItem(self.plot_item)

        self.plot_item_ema = pg.PlotDataItem()
        self.plot_item_ema.setPen(pg.mkPen('r'))
        self.graphWidget.addItem(self.plot_item_ema)

    def plot(self):
        last_point = self.data.get_slice.T[0,:]
        self.plot_item.setData(last_point)

        # we want to plot the EMA smoothed
        alpha = 0.5
        n = 5
        weights = alpha**np.arange(n)
        weights = weights / np.sum(weights)

        ema = np.squeeze(np.dot(self.data.get_slice[:,:n], weights[:, np.newaxis]))
        self.plot_item_ema.setData(ema)

class PlotChooser(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, key, buffer):
        super().__init__()
        self.key = key
        self.buffer = buffer

        self.widget = None

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(QtWidgets.QLabel(f'Graph: {key}'))
        self.layout().addLayout(buttons_layout)

        def add_button(plot_type):
            button = QtWidgets.QPushButton(f'Plot {plot_type}')
            # button = QtWidgets.QLabel(f'Plot {plot_type}')
            button.clicked.connect(lambda x: functools.partial(self.__handle_plot, plot_type)())
            buttons_layout.addWidget(button)

        shape = buffer.get_slice.shape
        if len(shape) == 1:
            add_button('single_dim')
        else:
            add_button('heatmap')
            add_button('4d')
            add_button('4d gl 3d')
            add_button('dist')
        add_button('hide')

    def __handle_plot(self, plot_type):
        if self.widget is not None:
            self.layout().removeWidget(self.widget)
            self.widget = None
    
        if plot_type == 'hide':
            self.widget = None
        elif plot_type == 'single_dim':
            self.widget = RealtimePlot(self.buffer, self.key)
        elif plot_type == 'heatmap':
            self.widget = HeatmapWidget(self.buffer, self.key)
        elif plot_type == '4d':
            self.widget = RealtimePlot4D(self.buffer, self.key)
        elif plot_type == '4d gl 3d':
            self.widget = GL3DPlot(self.buffer, self.key)
        elif plot_type == 'dist':
            self.widget = DistributionPlot(self.buffer, self.key)
        else:
            raise ValueError(f'unknown plot type: {plot_type}')

        if self.widget is not None:
            self.layout().addWidget(self.widget)
    
    def plot(self):
        if self.widget is not None:
            self.widget.plot()

class PlotChoice(QtWidgets.QWidget):
    def __init__(self, app, data_buffers):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.data_buffers = data_buffers
        self._widget_map = {}
        self.is_frozen = False

        freeze_button = QtWidgets.QPushButton(f'Freeze')
        freeze_button.clicked.connect(functools.partial(self.__handle_set_freeze, True))

        unfreeze_button = QtWidgets.QPushButton(f'Unfreeze')
        unfreeze_button.clicked.connect(functools.partial(self.__handle_set_freeze, False))

        self.layout().addWidget(qtgui.GuiHBoxContainer([freeze_button, unfreeze_button]))

    def __handle_set_freeze(self, freeze_value):
        self.is_frozen = freeze_value
    
    def update_publishers(self):
        buffer_tuples = {(node_id,key) for node_id in self.data_buffers.keys() for key in self.data_buffers[node_id].keys()}
        widget_tuples = set(self._widget_map.keys())

        for tup in buffer_tuples - widget_tuples:
            widget = PlotChooser(tup[1], self.data_buffers[tup[0]][tup[1]])
            self._widget_map[tup] = widget
            self.layout().addWidget(widget)

    def plot_all(self):
        if not self.is_frozen:
            for widget in self._widget_map.values():
                widget.plot()
    
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
        self.plot_choice.plot_all()
        self.__update_publishers()
        self.__poll_data()
        self.plot_choice.update_publishers()

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
                    if value is None:
                        continue

                    length = len(value) if hasattr(value, '__len__') else 1

                    if length == 1:
                        node_data_buffers.setdefault(key, fsgui.nparray.CircularArray(3000)).place(value)
                        self.buffered_writers.setdefault((node_id, key), fsgui.writer.BufferedHDFWriter(node_id, key, self.writer, 256)).append(value)
                    else:
                        node_data_buffers.setdefault(key, fsgui.nparray.MultiCircularArray((length, 3000))).place(value)
                
                data = sub.recv(timeout=0)


