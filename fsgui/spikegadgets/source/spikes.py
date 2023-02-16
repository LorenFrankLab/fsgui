import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import json
import numpy as np


class SpikesDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        self.network_location = network_location
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes Spikes',
            datatype='spikes',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes Spikes',
            }
        )

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
        import fsgui.spikegadgets.trodesnetwork as trodesnetwork
        trodesnetwork.SourceSubscriber('source.waveforms', server_address = f'{self.network_location.address}:{self.network_location.port}')
        return SpikesSource(network_location = self.network_location)

class SpikesSource:
    def __init__(self, network_location):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        import time

        def setup(data):
            import fsgui.network
            import fsgui.spikegadgets.trodesnetwork as trodesnetwork
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            # set up the actual subscriber
            data['spikes_sub'] = trodesnetwork.SourceSubscriber('source.waveforms', server_address = f'{network_location.address}:{network_location.port}')

        def workload(data):
            spikes_data = data['spikes_sub'].receive(timeout=50)
            if spikes_data is not None:
                data['publisher'].send(f'{json.dumps(spikes_data)}')
       
        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()
