import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import json
import time
import fsgui.network
import fsgui.spikegadgets.trodesnetwork as trodesnetwork

class TimestampDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        name='Trodes timestamps'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='timestamp',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
            }
        )

        self.network_location = network_location

    def write_template(self, config = None):
        if config is None:
            config = self.default()

        return [
            {
                'name': 'type_id',
                'type': 'hidden',
                'default': config['type_id'],
            },
            {
                'name': 'instance_id',
                'type': 'hidden',
                'default': config['instance_id'],
            },
            {
                'label': 'Nickname',
                'name': 'nickname',
                'type': 'string',
                'default': config['nickname'],
                'tooltip': 'This is the name the source is displayed as in menus.',
            },
        ]

    def build(self, config, addr_map):
        trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')
        return TimestampSource(network_location = self.network_location)

class TimestampSource:
    def __init__(self, network_location):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)


        def setup(data):
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            # set up the actual subscriber
            data['sub'] = trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{network_location.address}:{network_location.port}')

        def workload(data):
            timestamp_data = data['sub'].receive(timeout=50)
            if timestamp_data is not None:
                hardware_ts = timestamp_data['localTimestamp']
                data['publisher'].send(f'{hardware_ts}')
        
        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()
