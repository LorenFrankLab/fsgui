import logging
import time

class WidgetLoggingHandler(logging.Handler):
    def __init__(self, widget):
        self._widget = widget
        self._widget.setReadOnly(True)
        self._enabled = True

        super().__init__()
    
    def cleanup(self):
        self._enabled = False

    def emit(self, record):
        if self._enabled:
            level_string = {
                'DEBUG': '<font color="green">{}</font>',
                'INFO': '{}',
                'WARNING': '<font color="orang">{}</font>',
                'ERROR': '<font color="red">{}</font>',
            }.get(record.levelname, '{}').format(record.levelname)

            html_string = f'{time.ctime(record.created)}: {level_string} - {record.getMessage()}'
            
            self._widget.append(html_string)
