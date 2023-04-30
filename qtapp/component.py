from PyQt6 import QtCore, QtWidgets, QtSvgWidgets


import functools
import itertools

import qtgui
import qtgui.forms

import fsgui.util
import qtapp.collection

import fsgui.geometry
import shapely.geometry

import matplotlib.pyplot as plt
import matplotlib.backends.backend_qt5agg
import numpy as np

import time
import os

class FSGuiPlaceholderWidget(QtWidgets.QGroupBox):
    def __init__(self):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(QtWidgets.QLabel("There is no configuration selected."))

class FSGuiZeroMarginButtonCommandBox(qtgui.GuiButtonCommandBox):
    def __init__(self, button_list, status):
        super().__init__(button_list, status)
        self.layout().setContentsMargins(0,0,0,0)

class FSGuiNamedVerticalContainer(qtgui.GuiVBoxContainer):
    def __init__(self, items=[]):
        """
        items: a list of tuples (label, QWidget)
        """
        super().__init__(list(itertools.chain.from_iterable([(QtWidgets.QLabel(label), item) for label, item in items])))

class FSGuiZeroMarginTwoPane(qtgui.GuiRightPaneGrid):
    def __init__(self, left, right):
        super().__init__(left, right)
        self.layout().setContentsMargins(0,0,0,0)

class FSGuiPanelSplitter(QtWidgets.QWidget):
    def __init__(self, left, right):
        """
        left: a QWidget that goes on the left
        right: a QWidget that goes on the right
        """
        super().__init__()

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        splitter = QtWidgets.QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("QSplitter::handle { background-color: darkGray; margin-left: 3px; margin-right: 3px; }")
        self.layout().addWidget(splitter)

        splitter.addWidget(left)
        splitter.addWidget(right)

class PlotWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, plot_function):
        """
        plot_function: a plotting function that takes ax as argument
        """
        super().__init__()


        self._fig, ax = plt.subplots()
        plot_function(ax)

        self.layout().addWidget(matplotlib.backends.backend_qt5agg.FigureCanvas(self._fig))

    def __del__(self):
        # because the figures are managed globally by pyplot
        # we have to explicitly free the memory
        plt.close(self._fig)

class FSGuiDependencyGraphDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, graph=None):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.resize(500,500)
        self.setWindowTitle('FSGui dependency graph')

        self.graph_container = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.graph_container)

        if graph:
            self.update_graph(graph)
    
    def update_graph(self, graphviz_graph):
        self.graph_container.setWidget(qtapp.component.FSGuiDependencyGraphWidget(graphviz_graph))

class FSGuiDependencyGraphWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, graphviz_graph):
        """
        """
        super().__init__()

        content = graphviz_graph.pipe(encoding='utf-8', format='svg')
        widget = QtSvgWidgets.QSvgWidget()
        widget.renderer().setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        widget.load(bytes(content, encoding='utf-8'))

        self.layout().addWidget(widget)

class FSGuiRootEditor(qtgui.GuiVBoxContainer):
    """
    """

    edit_available = QtCore.pyqtSignal()

    def __init__(self, options, add_handler, item_data, editable=True):
        super().__init__()
        self._add_handler = add_handler

        self.selection = qtgui.forms.GuiFormSelectWidget(options = options, editable=editable)
        self.layout().addWidget(self.selection)
        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Set root node',
                'function': self.__handle_add,
                'enabled': editable,
            },
        ]))
    
    def __handle_add(self):
        self._add_handler(self.selection.read_value())

class FSGuiGateEditor(qtgui.GuiVBoxContainer):
    """
    """
    def __init__(self, options, add_handler, delete_handler, item_data, editable=True):
        super().__init__()
        self._add_handler = add_handler

        self.selection = qtgui.forms.GuiFormSelectWidget(options = options, editable=editable)
        self.layout().addWidget(self.selection)

        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Add node',
                'function': self.__handle_add,
                'enabled': editable,
            },
            {
                'label': 'Delete',
                'function': delete_handler,
                'enabled': editable,
            },
        ]))
    
    def __handle_add(self):
        selected = self.selection.read_value()
        self._add_handler(selected)

class FSGuiFilterEditor(qtgui.GuiVBoxContainer):
    """
    """
    def __init__(self, delete_handler, item_data, editable=True):
        super().__init__()
        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Delete',
                'function': delete_handler,
                'enabled': editable,
            },
        ]))

class FSGuiFilterSelectionWidget(qtgui.GuiVBoxContainer):
    """Placeholder widget for config types that don't exist yet
    """
    
    edit_available = QtCore.pyqtSignal()

    def __init__(self, filters, default = None, editable=True):
        super().__init__()

        self.filter_options = filters
        self.editable = editable

        self.tree_container = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.tree_container)

        self.selected_container = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.selected_container)

        self._tree_state = qtapp.collection.Tree(fsgui.util.UIDManager())
        if default is not None:
            self._tree_state.set_structure(default)

        self.__item_selected(None)
        self.__update_state()

    def __handle_add(self, target_id, item_data):
        """
        target_id: the id of the node who is the parent or None
        item_data: the data specifying 1) label 2) type 3) value
        """

        self._tree_state.add_item(target_id, {
            'label': item_data['label'],
            'type': item_data['type'],
            'value': item_data['value'],
        })

        self.__update_state()

    def __handle_delete(self, target_id):
        '''
        item_data: the item to delete
        '''
        self._tree_state.delete_by_id(target_id)

        self.__item_selected(None)
        self.__update_state()

    def __item_selected(self, item_data):
        # warning, we're breaking the pattern here of 'name' storing minimal information
        options = list(itertools.chain([
            {
                'label': 'AND Gate',
                'name': {'type': 'gate', 'value': 'gate-and', 'label': 'AND Gate'},
            },
            {
                'label': 'OR Gate',
                'name': {'type': 'gate', 'value': 'gate-or', 'label': 'OR Gate'},
            },
            {
                'label': 'NOT/NAND Gate',
                'name': {'type': 'gate', 'value': 'gate-nand', 'label': 'NOT/NAND Gate'},
            },
        ], [
            {
                'label': filt['label'],
                'name': {'type': 'filter', 'value': filt['name'], 'label': filt['label']}
            } for filt in self.filter_options
        ]))

        if item_data is None:
            self.selected_container.setWidget(FSGuiRootEditor(
                options,
                functools.partial(self.__handle_add, None),
                item_data,
                editable=self.editable,
            ))
        elif 'gate' == item_data['type']:
            self.selected_container.setWidget(FSGuiGateEditor(
                options,
                functools.partial(self.__handle_add, item_data['id']),
                functools.partial(self.__handle_delete, item_data['id']),
                item_data,
                editable=self.editable,
            ))
        elif 'filter' == item_data['type']:
            self.selected_container.setWidget(FSGuiFilterEditor(
                functools.partial(self.__handle_delete, item_data['id']),
                item_data,
                editable=self.editable,
            ))
        else:
            raise AssertionError(f'bad type: {item_data}')

    def __update_state(self):
        tree_state = {'children': []} 

        queue = []
        if not self._tree_state.is_empty():
            queue.append((tree_state, self._tree_state.get_root()))

        while len(queue) > 0:
            parent, node = queue.pop()

            new_node = {
                'label': node['data']['label'],
                'data': {
                    'type': node['data']['type'],
                    'id': node['id'],
                },
                'children': []
            }

            parent['children'].append(new_node)

            for child in node['children']:
                queue.append((new_node, child))

        tree = qtgui.GuiTreeSelection(tree_state['children'][0] if len(tree_state['children']) > 0 else None)
        tree.item_selected.connect(self.__item_selected)
        self.tree_container.setWidget(tree)

        self.edit_available.emit()


    def read_value(self):
        value = self._tree_state.get_root()
        return value

class FSGuiGeometrySelectionWidget(qtgui.GuiVBoxContainer):
    """
    """
    
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default = {'filename': '', 'zone_id': None}, editable=True):
        super().__init__()

        self.line = QtWidgets.QLineEdit(default['filename'])
        self.line.setEnabled(editable)
        self.line.textChanged.connect(lambda x: self.edit_available.emit())
        self.layout().addWidget(self.line)

        button = QtWidgets.QPushButton('Open geometry file')
        button.setEnabled(editable)
        button.clicked.connect(self.__handle_button)
        self.layout().addWidget(button)

        self.zone_selection_widget = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.zone_selection_widget)

        self.zone_selection = qtgui.forms.GuiFormSelectWidget(options=[{'name': default['zone_id'], 'label': 'Zone {}'.format(default['zone_id'])}], default=default['zone_id'], editable=editable)
        self.zone_selection_widget.setWidget(self.zone_selection)

        self.content = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.content)

        self.edit_available.connect(self.__handle_change)
        self.__handle_change()

    def __handle_change(self):
        import time
        self.content.setWidget(QtWidgets.QLabel(f'truth: {time.ctime()}'))

        filename = self.read_value()['filename']

        try:
            with open(filename, 'r') as f:
                content = f.read()

            import fsgui.geometry
            geometry_file = fsgui.geometry.TrackGeometryFileReader().read_string(content)

            self.zone_selection = qtgui.forms.GuiFormSelectWidget(options=[{'name': zone_id, 'label': f'Zone {zone_id}'} for zone_id in geometry_file['zone'].keys()], default=self.zone_selection.read_value())
            self.zone_selection.edit_available.connect(lambda: self.edit_available.emit())
            self.zone_selection_widget.setWidget(self.zone_selection)

            def plot_function(ax):
                ax.set_ylim(1, 0)
                ax.set_xlim(0, 1)

                for zone_id, inclusion_zone in geometry_file['zone'].items():
                    shapely_polygon = shapely.geometry.Polygon(inclusion_zone)
                    x,y = shapely_polygon.exterior.xy

                    if zone_id == self.read_value()['zone_id']:
                        ax.fill(x,y)
                    else:
                        ax.plot(x,y)

                    centroid_x, centroid_y = shapely_polygon.centroid.coords[0]
                    ax.text(centroid_x, centroid_y, f'{zone_id}')

            self.content.setWidget(PlotWidget(plot_function))
                
        except FileNotFoundError as e:
            self.content.setWidget(QtWidgets.QLabel(f'FileNotFound: {time.ctime()}'))

    def __handle_button(self):
        settings = QtCore.QSettings()
        dirname = settings.value('last_dirname_trackgeometry', QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.HomeLocation))
        (filename, _) = QtWidgets.QFileDialog().getOpenFileName(self, 'Open file', dirname, filter='Geometry files (*.trackgeometry)')
        if filename:
            settings.setValue('last_dirname_trackgeometry', os.path.dirname(filename))

        self.line.setText(f'{filename}')

    def read_value(self):
        return {
            'filename': self.line.text(),
            'zone_id': self.zone_selection.read_value()
        }




class SegmentFormWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    edit_available = QtCore.pyqtSignal()

    def __init__(self, label, default=(0,0), editable=True):
        super().__init__()

        self.layout().addWidget(QtWidgets.QLabel(f'<b>Segment: {label}</b>'))

        self._form = qtgui.forms.GuiForm([
            {
                'type': 'integer',
                'name': 'start',
                'lower': 0,
                'upper': 10000,
                'label': 'Starting bin (inclusive)',
                'default': default[0],
                'editable': editable,
            },
            {
                'type': 'integer',
                'name': 'end',
                'lower': 0,
                'upper': 10000,
                'label': 'Ending bin (inclusive)',
                'default': default[1],
                'editable': editable,
            },
        ])
        self._form.edit_available.connect(lambda: self.edit_available.emit())

        self.layout().addWidget(self._form)

    def read_value(self):
        val = self._form.read_value()
        return (val['start'],val['end'])

class FSGuiLinearizationSelectionWidget(qtgui.GuiVBoxContainer):
    """
    """
    
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default = None, editable=True):
        super().__init__()

        self.state = default if default is not None else {'filename': '', 'segments': []}

        self.line = QtWidgets.QLineEdit(self.state['filename'])
        self.line.setReadOnly(True)
        self.line.setEnabled(editable)
        self.layout().addWidget(self.line)

        button = QtWidgets.QPushButton('Open linearization file')
        button.clicked.connect(self.__handle_button)
        self.layout().addWidget(button)

        self.segment_specification_widget = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.segment_specification_widget)
        self.segment_widgets = []
        for segment_id, segment in enumerate(self.state['segments']):
            widget = SegmentFormWidget(segment_id, default=segment, editable=editable)
            widget.edit_available.connect(lambda: self.edit_available.emit())
            self.segment_widgets.append(widget)
        self.segment_specification_widget.setWidget(qtgui.GuiVBoxContainer(self.segment_widgets))

        self.plot_content = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.plot_content)

        self.__file_updated()

    def __handle_button(self):
        settings = QtCore.QSettings()
        dirname = settings.value('last_dirname_trackgeometry', QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.HomeLocation))
        (filename, _) = QtWidgets.QFileDialog().getOpenFileName(self, 'Open file', dirname, filter='Geometry files (*.trackgeometry)')
        if filename:
            settings.setValue('last_dirname_trackgeometry', os.path.dirname(filename))
        self.state['filename'] = filename
        self.__file_updated()
        self.edit_available.emit()

    def __file_updated(self):
        try:
            linearization_file = fsgui.geometry.TrackGeometryLinearizationFile(self.state['filename'])
            self.line.setText(self.state['filename'])
            self.__plot_linearization(linearization_file.linearization)

            self.segment_widgets.clear()
            for segment_id, _ in enumerate(linearization_file.linearization):
                if segment_id < len(self.state['segments']):
                    default = self.state['segments'][segment_id]
                else:
                    default = (0,0)
                widget = SegmentFormWidget(segment_id, default)
                widget.edit_available.connect(lambda: self.edit_available.emit())
                self.segment_widgets.append(widget)

            self.segment_specification_widget.setWidget(qtgui.GuiVBoxContainer(self.segment_widgets))

        except FileNotFoundError as e:
            self.plot_content.setWidget(QtWidgets.QLabel(f'FileNotFound: {time.ctime()}'))
    
    def __plot_linearization(self, linearization):
        def plot_function(ax):
            ax.invert_yaxis()
            for segment_id, line in enumerate(linearization):
                x1, y1 = line['start']
                x2, y2 = line['end']
                ax.arrow(x1, y1, x2-x1, y2-y1, length_includes_head=True, head_width=30)
                ax.annotate(f'{segment_id}', (np.mean([x1,x2]), np.mean([y1,y2])))
        content = PlotWidget(plot_function)
        content.setMinimumSize(500, 500)
        self.plot_content.setWidget(content)

    def read_value(self):
        value = {
            'filename': self.line.text(),
            'segments': [widget.read_value() for widget in self.segment_widgets]
        }
        return value

class FSGuiTetrodeSelectionWidget(qtgui.GuiVBoxContainer):
    """
    """
    # takes None
    # is_include: bool
    # tetrodes: [integer]
    # keep it as a dict
    
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default = None, editable=True):
        super().__init__()

        self.editable = editable

        initial_state = default if default is not None else {'is_include': True, 'tetrodes': [33,44,56]}

        self.set_include = qtgui.forms.GuiFormBooleanWidget(default=initial_state['is_include'], editable=editable)
        self.set_include.edit_available.connect(lambda: self.edit_available.emit())
        self.layout().addWidget(QtWidgets.QLabel('Include list of tetrodes'))
        self.layout().addWidget(self.set_include)

        self.add_button = QtWidgets.QPushButton('Add tetrode')
        self.add_button.setEnabled(editable)
        self.add_button.clicked.connect(self.__handle_add_button)
        self.layout().addWidget(self.add_button)

        self.remove_button = QtWidgets.QPushButton('Remove tetrode')
        self.remove_button.setEnabled(editable)
        self.remove_button.clicked.connect(self.__handle_remove_button)
        self.layout().addWidget(self.remove_button)

        self.tetrodes_layout = QtWidgets.QVBoxLayout()
        self.layout().addLayout(self.tetrodes_layout)

        self.tetrode_widgets = []
        for existing_tetrode in initial_state['tetrodes']:
            widget = qtgui.forms.GuiFormIntegerWidget(0, 100000, default=existing_tetrode, editable=editable)
            widget.edit_available.connect(lambda: self.edit_available.emit())
            self.tetrode_widgets.append(widget)
            self.tetrodes_layout.addWidget(widget)

    def __handle_add_button(self):
        widget = qtgui.forms.GuiFormIntegerWidget(0, 100000, editable=self.editable)
        widget.edit_available.connect(lambda: self.edit_available.emit())
        self.tetrode_widgets.append(widget)
        self.tetrodes_layout.addWidget(widget)

        self.edit_available.emit()

    def __handle_remove_button(self):
        widget = self.tetrode_widgets.pop()
        self.tetrodes_layout.removeWidget(widget)

        self.edit_available.emit()

    def read_value(self):
        return {
            'is_include': self.set_include.read_value(),
            'tetrodes': [widget.read_value() for widget in self.tetrode_widgets]
        }
