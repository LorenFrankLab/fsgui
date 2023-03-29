from PyQt6 import QtCore, QtWidgets
import functools

class GuiFormStringWidget(QtWidgets.QLineEdit):
    """Widget for strings
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default=None, tooltip=None, editable=True):
        super().__init__()

        if default:
            self.setText(default)
        if tooltip:
            self.setToolTip(tooltip)

        self.setEnabled(editable)
        
        self.textChanged.connect(lambda x: self.edit_available.emit())
        # self.editingFinished.connect(lambda: self.edit_available.emit())

    def read_value(self):
        return self.text()


class GuiFormSelectWidget(QtWidgets.QComboBox):
    """Widget for select
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self, options=None, default=None, tooltip=None, editable=True):
        super().__init__()
        if options is None:
            options = []

        options = [{'name': None, 'label': 'None'}] + options
        
        self.nameMap = {i: option['name'] for i, option in enumerate(options)}

        for option in options:
            self.addItem(option['label'])

        for index, item in enumerate(options):
            if item['name'] == default:
                self.setCurrentIndex(index)
                break

        if tooltip:
            self.setToolTip(tooltip)

        self.setEnabled(editable)

        self.currentIndexChanged.connect(lambda x: self.edit_available.emit())

    def read_value(self):
        index = self.currentIndex()
        if index not in self.nameMap:
            return None
        return self.nameMap[index]

class GuiFormDoubleWidget(QtWidgets.QDoubleSpinBox):
    """Widget for doubles
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self, lower=None, upper=None, decimals=None, default=None, units=None, special=None, step=None, tooltip=None, editable=True):
        # TODO: add proper defaulting w/ None
        super().__init__()
        if decimals is None:
            # this comes from the Qt default
            decimals = 2
        if default is None:
            default = 0
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setDecimals(decimals)
        if lower is not None and upper is not None:
            self.setRange(lower, upper)
        self.setValue(default)
        if units:
            self.setSuffix(f' {units}')
        if special:
            self.setSpecialValueText(special)
        if step:
            self.setSingleStep(step)
        if tooltip:
            self.setToolTip(tooltip)

        self.setEnabled(editable)
        
        self.textChanged.connect(lambda x: self.edit_available.emit())
        self.valueChanged.connect(lambda x: self.edit_available.emit())


    def read_value(self):
        value = self.value()
        return float(value)


class GuiFormIntegerWidget(QtWidgets.QSpinBox):
    """Widget for integers
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self, lower, upper, default=None, units=None, special=None, step=None, tooltip=None, editable=True):
        super().__init__()
        if default is None:
            default = 0
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setRange(lower, upper)
        # order matters here, so set the value after the range
        self.setValue(default)
        if units:
            self.setSuffix(f' {units}')
        if special:
            self.setSpecialValueText(special)
        if step:
            self.setSingleStep(step)
        if tooltip:
            self.setToolTip(tooltip)

        self.setEnabled(editable)

        self.textChanged.connect(lambda x: self.edit_available.emit())
        self.valueChanged.connect(lambda x: self.edit_available.emit())

    def read_value(self) -> int:
        value = self.value()
        # cast shouldn't be necessary
        return int(value)


class GuiFormBooleanWidget(QtWidgets.QCheckBox):
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default, tooltip=None, editable=True):
        super().__init__()
        if default is None:
            default = False
        self.setChecked(default)
        if tooltip:
            self.setToolTip(tooltip)
        
        self.setEnabled(editable)

        self.stateChanged.connect(lambda x: self.edit_available.emit())

    def read_value(self) -> bool:
        value = self.isChecked()
        return value

class GuiFormHiddenWidget(QtWidgets.QWidget):
    """Placeholder widget for config types that don't exist yet
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self, default):
        super().__init__()
        self.default = default

    def read_value(self):
        return self.default

class GuiFormNoneWidget(QtWidgets.QLabel):
    """Placeholder widget for config types that don't exist yet
    """
    edit_available = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__("None")

    def read_value(self) -> None:
        return None

class GuiForm(QtWidgets.QWidget):
    # transmits the new data
    edit_available = QtCore.pyqtSignal(object)

    def __init__(self, param_config, extra=[], editable=True, send_message_function=None):
        super().__init__()

        self.setLayout(QtWidgets.QFormLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.widgets = {}

        widget_builders_list = [
            ('string', lambda i, e: GuiFormStringWidget(default=i.get('default'),
                                                tooltip=i.get('tooltip'),
                                                editable=e)),
            ('select', lambda i, e: GuiFormSelectWidget(options=i.get('options'),
                                                default=i.get('default'),
                                                tooltip=i.get('tooltip'),
                                                editable=e)),
            ('integer', lambda i, e: GuiFormIntegerWidget(default=i.get('default'),
                                                lower=i['lower'],
                                                upper=i['upper'],
                                                units=i.get('units'),
                                                special=i.get('special'),
                                                step=i.get('step'),
                                                tooltip=i.get('tooltip'),
                                                editable=e)),
            ('double', lambda i, e: GuiFormDoubleWidget(default=i.get('default'),
                                                lower=i.get('lower'),
                                                upper=i.get('upper'),
                                                decimals=i.get('decimals'),
                                                units=i.get('units'),
                                                special=i.get('special'),
                                                step=i.get('step'),
                                                tooltip=i.get('tooltip'),
                                                editable=e)),
            ('boolean', lambda i, e: GuiFormBooleanWidget(default=i.get('default'),
                                                tooltip=i.get('tooltip'),
                                                editable=e)),
            ('hidden', lambda i, e: GuiFormHiddenWidget(default=i.get('default'))),
            ('none', lambda i, e: GuiFormNoneWidget())
        ]

        for option in extra:
            widget_builders_list.append(option)

        widget_builders = {
            k: v for k,v in widget_builders_list
        }

        def print_message(varname, widget):
            value = widget.read_value()
            send_message_function(varname, value)

        for params in param_config:
            live_editable = params.get('live_editable', False)
            widget_editable = editable or not editable and live_editable

            widget = widget_builders.get(params['type'], widget_builders['none'])(params, widget_editable)
            self.widgets[params['name']] = widget

            if params['type'] != 'hidden':
                self.layout().addRow(params['label'], widget)

                if not editable and params.get('live_editable'):
                    button = QtWidgets.QPushButton('Update')
                    button.clicked.connect(functools.partial(print_message, varname=params['name'], widget=widget))
                    self.layout().addRow('', button)

            widget.edit_available.connect(lambda: self.edit_available.emit(self.read_value()))

    def read_value(self):
        return {key: self.widgets[key].read_value() for key in self.widgets.keys()}
