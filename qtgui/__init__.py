from PyQt6 import QtCore, QtWidgets
import functools
import time

class GuiZeroMarginVBoxLayoutWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

class GuiKeyboardCommandBox(GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, options):
        super().__init__()
        self.function_map = { option['key']: option['function'] for option in options }
        self.grabKeyboard()

        
    def keyPressEvent(self, event):
        function = self.function_map.get(event.text(), None)
        if function is not None:
            function()

class GuiButtonCommandBox(GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, param_list, state=None):
        """
        param_list: list of dicts (label, enabled, function)
        state: the state to render things
        """
        super().__init__()
        self.layout().setContentsMargins(0,0,0,0)

        def extract_value_state(params, key, state, default=None):
            if key in params:
                if isinstance(params[key], dict):
                    if state in params[key]:
                        return params[key][state]
                    elif 'default' in params[key]:
                        return params[key]['default']
                    else:
                        return default
                else:
                    return params[key]
            else:
                return default

        for params in param_list:
            label = extract_value_state(params, 'label', state)
            function = extract_value_state(params, 'function', state)
            enabled = extract_value_state(params, 'enabled', state, default=True)

            button = QtWidgets.QPushButton(label)
            button.clicked.connect(function)
            button.setEnabled(enabled)
            self.layout().addWidget(button)

class GuiRightPaneGrid(QtWidgets.QWidget):
    def __init__(self, left, right):
        """
        left: a QWidget that goes on the left
        right: a QWidget that goes on the right
        """
        super().__init__()

        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(left, 0, 0, 1, 1)
        self.layout().addWidget(right, 0, 1, 1, 1)
        # column zero, no stretch
        self.layout().setColumnStretch(0, 0)
        # column one, some stretch
        self.layout().setColumnStretch(1, 1)


class GuiVBoxContainer(QtWidgets.QWidget):
    def __init__(self, widgets = []):
        """
        widgets: a list of widgets
        """
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        for widget in widgets:
            self.layout().addWidget(widget)

class GuiHBoxContainer(QtWidgets.QWidget):
    def __init__(self, widgets = []):
        """
        widgets: a list of widgets
        """
        super().__init__()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        for widget in widgets:
            self.layout().addWidget(widget)

class GuiContainerWidget(QtWidgets.QWidget):
    def __init__(self, placeholder=None):
        super().__init__()
        self._current_item = None
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)

        if placeholder is not None:
            self.setWidget(placeholder)
    
    def setWidget(self, widget):
        """
        Visually removes the old widget from the layout and deletes it. The
        destructor is called as long as you're not holding pointers it. Use
        currentItem() to get a reference to it.

        It should not be used in high-performance applications where you need to
        create and delete objects quickly.
        """
        if self._current_item is not None:
            self._current_item.deleteLater()
            self._current_item = None
        self._current_item = widget
        self.layout().addWidget(widget)
    
    def currentItem(self):
        return self._current_item

class GuiListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, label, data):
        """
        """
        super().__init__(label)
        self.item_data = data

class GuiListSelection(QtWidgets.QWidget):
    item_selected = QtCore.pyqtSignal(object)

    def __init__(self, items=[], select_predicate=None, item_constructor = GuiListWidgetItem):
        """
        items: an iterator of (label, data) tuples
        render_function: a conditional function that will render the item widget based on item_data
        """
        super().__init__()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self._list = QtWidgets.QListWidget()
        self.layout().addWidget(self._list)

        selection_made = False
        for label, data in items:
            item = item_constructor(label, data)

            self._list.addItem(item)

            if select_predicate and select_predicate(data) and not selection_made:
                self._list.setCurrentItem(item)
                selection_made = True
        
        self._list.itemPressed.connect(lambda x: self.item_selected.emit(self.current_item()))
    
    def current_item(self):
        item = self._list.currentItem()
        if item is not None:
            return item.item_data
        else:
            return None
    
    def deselect(self):
        self._list.setCurrentItem(None)

class GuiMultiListSelection(QtCore.QObject):
    item_selected = QtCore.pyqtSignal(object)

    def __init__(self, lists=[]):
        """
        lists: a list of GuiListSelection
        """
        super().__init__()

        self.lists = { key: value for key, value in enumerate(lists)}

        for key, lst in self.lists.items():
            lst.item_selected.connect(functools.partial(self.__handle_changed, key))

    def __handle_changed(self, key, item_data):
        for key_idx, lst in self.lists.items():
            if key_idx != key:
                lst.deselect()
        self.item_selected.emit(item_data)

    def current_item(self):
        for lst in self.lists.values():
            item = lst.current_item()
            if item is not None:
                return item
        return None

    def deselect(self):
        for lst in self.lists.values():
            lst.deselect()

class GuiSelectDisplayWidget(GuiZeroMarginVBoxLayoutWidget):
    def __init__(self, display_ctx, items, selector_ctx=GuiListSelection):
        """
        display_ctx: a constructor for a QWidget to display item_data; if it needs information, use partials
        items: list of (label, item_data) tuples
        selector_ctx: optionally can specify a GuiSearchListSelection using partials
        """
        super().__init__()

        selector = selector_ctx(items)
        display_container = GuiContainerWidget()
        selector.item_selected.connect(lambda item_data: display_container.setWidget(display_ctx(item_data)))

        self.layout().addWidget(GuiRightPaneGrid(
            left = selector,
            right = display_container
        ))

class GuiIntervalTimer(QtCore.QObject):
    def __init__(self, function, interval_ms):
        """
        function: some callback to be periodically called
        interval_ms: the time to wait between calling
        """
        # we keep a pointer to the timer as long as this is alive
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(function)
        self.timer.start(interval_ms)


class GuiTreeSelection(QtWidgets.QWidget):
    """
    Interface:
    - item_selected: hands us just the data associated with the item
    """
    item_selected = QtCore.pyqtSignal(object)

    def __init__(self, items=None, select_predicate=None):
        """
        """
        super().__init__()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderLabels([''])
        self.layout().addWidget(self._tree)

        queue = []
        if items is not None:
            queue.append((self._tree, items))

        selection_made = False
        while len(queue) > 0:
            root, node = queue.pop()
            data = node['data']

            item = QtWidgets.QTreeWidgetItem(root, [node['label']])
            item.item_data = data
            self._tree.expandItem(item)

            if select_predicate and select_predicate(data) and not selection_made:
                self._tree.setCurrentItem(item)
                selection_made = True

            if 'children' in node:
                for child in node['children']:
                    queue.append((item, child))
        self._tree.itemSelectionChanged.connect(lambda: self.item_selected.emit(self.current_item()))
    def current_item(self):
        item = self._tree.currentItem()
        if item is not None:
            return item.item_data
        else:
            return None

    def deselect(self):
        self._tree.setCurrentItem(None)

def run_qt_app(constructor):
    """
    Runs a widget or window in Qt. If your constructor needs additional parameters,
    just use partial application from functools. You can't pass constructed objects
    because they have to be created in a context.

    This takes control of the thread and eventually returns a status code.
    """
    # we decline to pass args
    app = QtWidgets.QApplication([])
    window = constructor()
    window.show()
    return app.exec()
