from PyQt6 import QtCore, QtWidgets, QtSvgWidgets


import functools
import itertools

import qtgui
import qtgui.forms

import fsgui.util
import qtapp.collection

import shapely.geometry

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


class PlotWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, plot_function):
        """
        plot_function: a plotting function that takes ax as argument
        """
        super().__init__()

        import matplotlib.pyplot as plt
        import matplotlib.backends.backend_qt5agg

        self._fig, ax = plt.subplots()
        plot_function(ax)

        self.layout().addWidget(matplotlib.backends.backend_qt5agg.FigureCanvas(self._fig))

    def __del__(self):
        # because the figures are managed globally by pyplot
        # we have to explicitly free the memory
        plt.close(self._fig)

class FSGuiDependencyGraphWidget(qtgui.GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, graphviz_graph):
        """
        """
        super().__init__()

        content = graphviz_graph.pipe(encoding='utf-8', format='svg')
        widget = QtSvgWidgets.QSvgWidget()
        widget.load(bytes(content, encoding='utf-8'))

        self.layout().addWidget(widget)

class FSGuiRootEditor(qtgui.GuiVBoxContainer):
    """
    """

    edit_available = QtCore.pyqtSignal()

    def __init__(self, options, add_handler, item_data):
        super().__init__()
        self._add_handler = add_handler

        self.selection = qtgui.forms.GuiFormSelectWidget(options = options)
        self.layout().addWidget(self.selection)
        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Set root node',
                'function': self.__handle_add,
            },
        ]))
    
    def __handle_add(self):
        self._add_handler(self.selection.read_value())

class FSGuiGateEditor(qtgui.GuiVBoxContainer):
    """
    """
    def __init__(self, options, add_handler, delete_handler, item_data):
        super().__init__()
        self._add_handler = add_handler

        self.selection = qtgui.forms.GuiFormSelectWidget(options = options)
        self.layout().addWidget(self.selection)

        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Add node',
                'function': self.__handle_add,
            },
            {
                'label': 'Delete',
                'function': delete_handler,
            },
        ]))
    
    def __handle_add(self):
        selected = self.selection.read_value()
        self._add_handler(selected)

class FSGuiFilterEditor(qtgui.GuiVBoxContainer):
    """
    """
    def __init__(self, delete_handler, item_data):
        super().__init__()
        self.layout().addWidget(qtgui.GuiButtonCommandBox([
            {
                'label': 'Delete',
                'function': delete_handler,
            },
        ]))

class FSGuiFilterSelectionWidget(qtgui.GuiVBoxContainer):
    """Placeholder widget for config types that don't exist yet
    """
    
    edit_available = QtCore.pyqtSignal()

    def __init__(self, filters, default = None):
        super().__init__()

        self.filter_options = filters

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
                item_data
            ))
        elif 'gate' == item_data['type']:
            self.selected_container.setWidget(FSGuiGateEditor(
                options,
                functools.partial(self.__handle_add, item_data['id']),
                functools.partial(self.__handle_delete, item_data['id']),
                item_data
            ))
        elif 'filter' == item_data['type']:
            self.selected_container.setWidget(FSGuiFilterEditor(
                functools.partial(self.__handle_delete, item_data['id']),
                item_data
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

    def __init__(self, default = None):
        super().__init__()

        self.filename = default

        self.line = QtWidgets.QLineEdit(self.filename)
        self.line.textChanged.connect(lambda x: self.edit_available.emit())
        self.layout().addWidget(self.line)

        button = QtWidgets.QPushButton('Open geometry file')
        button.clicked.connect(self.__handle_button)
        self.layout().addWidget(button)

        self.content = qtgui.GuiContainerWidget()
        self.layout().addWidget(self.content)

        self.edit_available.connect(self.__handle_change)
        self.__handle_change()

    def __handle_change(self):
        import time
        self.content.setWidget(QtWidgets.QLabel(f'truth: {time.ctime()}'))

        filename = self.read_value()

        try:
            with open(filename, 'r') as f:
                content = f.read()

            import fsgui.geometry

            reader = fsgui.geometry.TrackGeometryFileReader()
            geometry_file = reader.read_string(content)

            shapely_polygon = shapely.geometry.Polygon(geometry_file.get_inclusion_zone[0].polygon.nodes)

            def plot_function(ax):
                x,y = shapely_polygon.exterior.xy
                ax.plot(x,y)

            # self.content.setWidget(QtWidgets.QTextEdit(f'{geometry_file}'))
            self.content.setWidget(PlotWidget(plot_function))
                
        except FileNotFoundError as e:
            self.content.setWidget(QtWidgets.QLabel(f'FileNotFound: {time.ctime()}'))

        # open the file
        # check the file out
        # plot the file

    def __handle_button(self):
        dialog = QtWidgets.QFileDialog()
        dialog.setNameFilter('Geometry files (*.trackgeometry)')
        dialog.fileSelected.connect(lambda filename: self.line.setText(f'{filename}'))
        dialog.exec()

    def read_value(self):
        return self.line.text()