from PyQt6 import QtWidgets, QtCore, QtGui

import fsgui.application
import qtapp.component
import qtgui
import functools
import qtapp.logging

import traceback
import logging
import graphviz
   
class FSGuiNodeConfigWidget(qtgui.GuiVBoxContainer):
    edit_node = QtCore.pyqtSignal(object)
    build_node = QtCore.pyqtSignal()
    unbuild_node = QtCore.pyqtSignal()
    delete_node = QtCore.pyqtSignal()

    def __init__(self, datatype, typename, form_config, status, form_extra=[]):
        """
        """
        super().__init__()

        self.layout().addStretch(1)
        self.layout().addWidget(QtWidgets.QLabel(f'<h3>Configure existing node</h3>'))
        self.layout().addWidget(QtWidgets.QLabel(f'<b>datatype: {datatype}</b>'))
        self.layout().addWidget(QtWidgets.QLabel(f'<b>type: {typename}</b>'))
        self._form = qtgui.forms.GuiForm(form_config, editable=(not status == 'built'), extra=form_extra)
        self._form.edit_available.connect(lambda x: self.edit_node.emit(x))
        self.layout().addWidget(self._form)
        self.layout().addWidget(qtapp.component.FSGuiZeroMarginButtonCommandBox([
            {
                'label': {
                    'built': 'Unbuild',
                    'default': 'Build',
                },
                'function': {
                    'built': lambda: self.unbuild_node.emit(),
                    'default': lambda: self.build_node.emit(),
                } 
            },
            {
                'label': 'Delete',
                'enabled': {
                    'built': False,
                    'default': True,
                },
                'function': lambda: self.delete_node.emit(),
            },
        ], status))
        self.layout().addStretch(2)

class FSGuiNodeAddWidget(qtgui.GuiVBoxContainer):
    create_node = QtCore.pyqtSignal(object)

    def __init__(self, datatype, typename, form_config, form_extra=[]):
        super().__init__()

        self.layout().addStretch(1)
        self.layout().addWidget(QtWidgets.QLabel(f'<h3>Configure new node</h3>'))
        self.layout().addWidget(QtWidgets.QLabel(f'<b>datatype: {datatype}</b>'))
        self.layout().addWidget(QtWidgets.QLabel(f'<b>type: {typename}</b>'))
        self._form = qtgui.forms.GuiForm(form_config, extra=form_extra)
        self.layout().addWidget(self._form)
        self.layout().addWidget(qtapp.component.FSGuiZeroMarginButtonCommandBox([
            {
                'label': 'Add node',
                'function': lambda x: self.create_node.emit(self._form.read_value()),
            },
        ], None))
        self.layout().addStretch(2)

class NodeListWidgetItem(qtgui.GuiListWidgetItem):
    def __init__(self, label, data):
        status = data['status']
        super().__init__(f'{label} ({status})', data)

        if status == 'error':
            background = QtGui.QBrush(QtGui.QColor.fromRgb(255,155,155))
        elif status == 'built':
            background = QtGui.QBrush(QtGui.QColor.fromRgb(155,255,155))
        elif status == 'unbuilt':
            background = QtGui.QBrush()

        self.setBackground(background)

class FSGuiNodeList(qtgui.GuiZeroMarginVBoxLayoutWidget):
    item_selected = QtCore.pyqtSignal(object)

    def __init__(self, items=[], selected_instance_id=None):
        super().__init__()
        list_widget = qtgui.GuiListSelection(
            [(tag, {'instance_id': instance_id, 'status': status})
            for tag, instance_id, status, form_config in items],
            item_constructor=NodeListWidgetItem,
            select_predicate=lambda data: selected_instance_id == data['instance_id'])
        list_widget.item_selected.connect(lambda x: self.item_selected.emit(x))
        self.layout().addWidget(list_widget)

class FSGuiTypeList(qtgui.GuiZeroMarginVBoxLayoutWidget):
    item_selected = QtCore.pyqtSignal(object)
    def __init__(self, items=[], selected_instance_id=None):
        super().__init__()
        list_widget = qtgui.GuiListSelection(
            [(tag, {'type_id': type_id})
            for type_id, tag, form_config in items],
            select_predicate=lambda data: selected_instance_id == data['type_id']
            )
        list_widget.item_selected.connect(lambda x: self.item_selected.emit(x))
        self.layout().addWidget(list_widget)




class FileMenu(QtWidgets.QMenu):
    new_triggered = QtCore.pyqtSignal(object)
    open_triggered = QtCore.pyqtSignal(object)
    save_triggered = QtCore.pyqtSignal()
    save_as_triggered = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__('File', parent=parent)

        self.new_action = QtGui.QAction('New Configuration File...', self)
        self.new_action.setShortcut('Ctrl+N')
        self.addAction(self.new_action)
        self.new_action.triggered.connect(lambda: self.new_triggered.emit(self.__get_save_filename()))

        self.addSeparator()

        self.open_action = QtGui.QAction('Open Configuration File...', self)
        self.open_action.setShortcut('Ctrl+O')
        self.addAction(self.open_action)
        self.open_action.triggered.connect(lambda: self.open_triggered.emit(self.__get_existing_filename()))

        self.addSeparator()

        self.save_action = QtGui.QAction('Save Configuration File', self)
        self.save_action.setShortcut('Ctrl+S')
        self.addAction(self.save_action)
        self.save_action.triggered.connect(lambda: self.save_triggered.emit())

        self.save_as_action = QtGui.QAction('Save Configuration File As...', self)
        self.save_as_action.setShortcut('Ctrl+Shift+S')
        self.addAction(self.save_as_action)
        self.save_as_action.triggered.connect(lambda: self.save_as_triggered.emit(self.__get_save_filename()))

    def __get_save_filename(self):
        (filename, _) = QtWidgets.QFileDialog().getSaveFileName(parent=self, filter='FSGui config files (*.yaml)')
        return filename

    def __get_existing_filename(self):
        (filename, _) = QtWidgets.QFileDialog().getOpenFileName(parent=self, filter='FSGui config files (*.yaml)')
        return filename

class FSGuiWindow(QtWidgets.QMainWindow):
    def __init__(self, args, app):
        super().__init__()
        self.app = app

        self.widget = FSGuiWidget(args, app, parent=self)
        self.setCentralWidget(self.widget)
        self.setWindowTitle('FSGui')

        menu = FileMenu(self)
        self.menuBar().addMenu(menu)

        menu.new_triggered.connect(lambda x: print(f'triggered new {x}'))
        menu.open_triggered.connect(lambda x: print(f'triggered open {x}'))
        menu.save_triggered.connect(lambda: print('triggered save'))
        menu.save_as_triggered.connect(lambda x: print(f'triggered save as {x}'))

class FSGuiWidget(QtWidgets.QWidget):
    def __init__(self, args, app, parent=None):
        super().__init__(parent=parent)

        self.app = app

        log_text_widget = QtWidgets.QTextEdit()
        self.__setup_logger(log_text_widget)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(QtWidgets.QLabel('<h1>FSGUI</h1>'))
        self.layout().addWidget(QtWidgets.QLabel(f'<i>{args}</i>'))

        self.sources_container = qtgui.GuiContainerWidget()
        self.source_types_container = qtgui.GuiContainerWidget()
        self.filters_container = qtgui.GuiContainerWidget()
        self.filter_types_container = qtgui.GuiContainerWidget()
        self.actions_container = qtgui.GuiContainerWidget()
        self.action_types_container = qtgui.GuiContainerWidget()
        self.config_container = qtgui.GuiContainerWidget()

        self.graph_dialog = qtapp.component.FSGuiDependencyGraphDialog(self)
        self.graph_dialog.show()

        # self.graph_container = qtgui.GuiContainerWidget(f=QtCore.Qt.WindowType.Window)

        self.layout().addWidget(qtapp.component.FSGuiZeroMarginTwoPane(
            qtapp.component.FSGuiNamedVerticalContainer([
                ('<h2>Sources</h2>', qtgui.GuiHBoxContainer([
                    qtapp.component.FSGuiNamedVerticalContainer([('Edit source', self.sources_container)]),
                    qtapp.component.FSGuiNamedVerticalContainer([('Add source', self.source_types_container)])
                ])),
                ('<h2>Filters</h2>', qtgui.GuiHBoxContainer([
                    qtapp.component.FSGuiNamedVerticalContainer([('Edit filter', self.filters_container)]),
                    qtapp.component.FSGuiNamedVerticalContainer([('Add filter', self.filter_types_container)])
                ])),
                ('<h2>Actions</h2>', qtgui.GuiHBoxContainer([
                    qtapp.component.FSGuiNamedVerticalContainer([('Edit action', self.actions_container)]),
                    qtapp.component.FSGuiNamedVerticalContainer([('Add action', self.action_types_container)])
                ]))
            ]),
            qtgui.GuiVBoxContainer([
                self.config_container,
                # self.graph_container,
            ]),
        ))

        self.layout().addStretch(1)

        self.layout().addWidget(log_text_widget)

        self.selected_instance_id = None
        self.__refresh_list()

    
    def __setup_logger(self, text_edit_widget):
        import logging

        self.log_handler = qtapp.WidgetLoggingHandler(text_edit_widget)
        self.log_handler.setLevel(logging.DEBUG)

        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(self.log_handler)
    
    def __del__(self):
        self.log_handler.cleanup()

    def __update_graph(self):
        dot = graphviz.Digraph(comment='Dependency graph', engine='dot') 
        dot.attr(rankdir='RL')


        previous = None

        for node_id, node_config in self.app.added_nodes.items():
            dot.node(node_id, node_config.nickname)  
            for child_id in self.app.get_node_children_ids(node_id):
                if child_id is not None:
                    dot.edge(child_id, node_id, constraint='false')

        dot = dot.unflatten(stagger=3, fanout=True, chain=3)
 
        # self.graph_container.setWidget(qtapp.component.FSGuiDependencyGraphWidget(dot))
        self.graph_dialog.update_graph(dot)

    def __refresh_list(self):
        """
        """
        self.__update_graph()

        config = self.app.get_configs()

        sources_list = FSGuiNodeList(items=config['source_nodes'], selected_instance_id=self.selected_instance_id)
        sources_list.item_selected.connect(self.__handle_node_selected)
        self.sources_container.setWidget(sources_list)

        source_types_list = FSGuiTypeList(items=config['source_types'], selected_instance_id=self.selected_instance_id)
        source_types_list.item_selected.connect(self.__handle_type_selected)
        self.source_types_container.setWidget(source_types_list)

        filters_list = FSGuiNodeList(items=config['filter_nodes'], selected_instance_id=self.selected_instance_id)
        filters_list.item_selected.connect(self.__handle_node_selected)
        self.filters_container.setWidget(filters_list)

        filter_types_list = FSGuiTypeList(items=config['filter_types'], selected_instance_id=self.selected_instance_id)
        filter_types_list.item_selected.connect(self.__handle_type_selected)
        self.filter_types_container.setWidget(filter_types_list)

        actions_list = FSGuiNodeList(items=config['action_nodes'], selected_instance_id=self.selected_instance_id)
        actions_list.item_selected.connect(self.__handle_node_selected)
        self.actions_container.setWidget(actions_list)

        action_types_list = FSGuiTypeList(items=config['action_types'], selected_instance_id=self.selected_instance_id)
        action_types_list.item_selected.connect(self.__handle_type_selected)
        self.action_types_container.setWidget(action_types_list)

    def __refresh_config_box(self):
        self.__set_config_box(self.selected_instance_id)

    def __handle_node_selected(self, item_data):
        self.__set_config_box(item_data['instance_id'])
        self.__refresh_list()

    def __get_form_extra(self):
        # access app and get the latest nodes...

        # construct this by filtering them...
        # filter here, then move logic to application

        def get_options_datatype(datatype):
            return [
                {'name': node.instance_id, 'label': node.param_config['nickname']}
                for node in self.app.get_nodes_datatype(datatype)]
            
        form_extra = [
            ('node:float', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('float'), default=i.get('default'))),
            ('node:discrete_distribution', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('discrete_distribution'), default=i.get('default'))),
            ('node:bin_id', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('bin_id'), default=i.get('default'))),
            ('node:bool', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('bool'), default=i.get('default'))),
            ('node:spikes', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('spikes'), default=i.get('default'))),
            ('node:timestamp', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('timestamp'), default=i.get('default'))),
            ('node:point2d', lambda i: qtgui.forms.GuiFormSelectWidget(options=get_options_datatype('point2d'), default=i.get('default'))),
            ('node:tree', lambda i: qtapp.component.FSGuiFilterSelectionWidget(filters=get_options_datatype('bool'), default=i.get('default'))),
            ('geometry', lambda i: qtapp.component.FSGuiGeometrySelectionWidget(default=i.get('default'))),
        ]
        return form_extra

    def __set_config_box(self, instance_id):
        if instance_id is None:
            self.config_container.setWidget(qtapp.component.FSGuiPlaceholderWidget())
            self.selected_instance_id = None
        elif instance_id in self.app.added_nodes:
            node = self.app.added_nodes[instance_id]
            # toss in some data: instance_id, form_config, status
            type_id = node.type_id
            datatype = self.app.available_types[type_id].type_object.datatype()
            typename = self.app.available_types[type_id].type_object.name()
            form_config = self.app.available_types[node.type_id].type_object.write_template(node.param_config)
            widget = FSGuiNodeConfigWidget(datatype, typename, form_config, node.status, self.__get_form_extra())
            widget.edit_node.connect(self.__handle_edit_node)
            widget.build_node.connect(self.__handle_build_node)
            widget.unbuild_node.connect(self.__handle_unbuild_node)
            widget.delete_node.connect(self.__handle_delete_node)
            self.config_container.setWidget(widget)
            self.selected_instance_id = instance_id
        else:
            raise ValueError('instance_id should either be None or a valid id')

    def __handle_type_selected(self, item_data):
        if item_data is None:
            return

        type_id = item_data['type_id']
        datatype = self.app.available_types[type_id].type_object.datatype()
        typename = self.app.available_types[type_id].type_object.name()
        form_config = self.app.available_types[type_id].type_object.write_template()

        widget = FSGuiNodeAddWidget(datatype, typename, form_config, self.__get_form_extra())
        widget.create_node.connect(self.__handle_create_node)

        self.config_container.setWidget(widget)

        # this is where it gets messy
        self.selected_instance_id = item_data['type_id']
        self.__refresh_list()

    def __handle_create_node(self, config):
        self.selected_instance_id = self.app.create_node(config)
        self.__refresh_list()
        self.__refresh_config_box()

    def __handle_edit_node(self, config):
        try:
            self.app.edit_node(config)
        except Exception as e:
            self.__log_exception(e)
        self.__refresh_list()

    def __handle_build_node(self):
        try:
            self.app.build_node(self.selected_instance_id)
        except Exception as e:
            self.__log_exception(e)
            logging.exception(f'Error while recursively building parent node: {self.app.added_nodes[self.selected_instance_id].nickname}')

        self.__refresh_list()
        self.__refresh_config_box()
    
    def __log_exception(self, e):
        trace_string = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        logging.info(f'<pre>{trace_string}</pre>')
        logging.exception(f'{repr(e)}')

    def __handle_unbuild_node(self):
        try:
            self.app.unbuild_node(self.selected_instance_id)
        except Exception as e:
            self.__log_exception(e)
        self.__refresh_list()
        self.__refresh_config_box()

    def __handle_delete_node(self):
        try:
            self.app.delete_node(self.selected_instance_id)
        except Exception as e:
            self.__log_exception(e)
        self.__refresh_list()
        self.selected_instance_id = None
        self.__refresh_config_box()
