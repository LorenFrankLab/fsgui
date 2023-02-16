import sys
import logging
import functools

import fsgui.application
import fsgui.config
import fsgui.mock
import fsgui.filter
import fsgui.spikegadgets
import qtapp
import qtgui

if __name__ == "__main__":
    try:
        args = fsgui.spikegadgets.trodes.TrodesSpawnArgParser().parse_args(sys.argv)
        network = fsgui.spikegadgets.trodes.TrodesNetworkLocation(
            args['serverAddress'],
            args['serverPort']
        )
    except Exception as e:
        logging.warning('command line arguments were not found, using default network location')
        network = fsgui.spikegadgets.trodes.TrodesNetworkLocation("tcp://127.0.0.1", 49152)

    qtgui.run_qt_app(functools.partial(
        qtapp.window.FSGuiWindow,
        sys.argv,
        fsgui.application.FSGuiApplication(
            node_providers = [
                fsgui.spikegadgets.SpikeGadgetsNodeProvider(network_location=network),
                fsgui.filter.FilterProvider(),
                fsgui.mock.MockNodeProvider(),
            ],
            config = fsgui.config.FileConfig('config.yaml'),
        )
    ))
