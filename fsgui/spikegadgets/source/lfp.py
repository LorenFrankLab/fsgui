import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import json


class LFPDataType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        super().__init__(
            type_id=type_id,
            node_class='source',
            name='Trodes LFP',
            datatype='float',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': 'Trodes LFP',
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
        import fsgui.spikegadgets.trodesnetwork as trodesnetwork
        trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{self.network_location.address}:{self.network_location.port}')
        return LFPSource(network_location = self.network_location)

class LFPSource:
    def __init__(self, network_location):
        pipe_recv, pipe_send = mp.Pipe(duplex=False)

        import time

        def setup(data):
            import fsgui.network
            import fsgui.spikegadgets.trodesnetwork as trodesnetwork
            data['publisher'] = fsgui.network.UnidirectionalChannelSender()
            pipe_send.send(data['publisher'].get_location())

            # set up the actual subscriber
            data['lfp_sub'] = trodesnetwork.SourceSubscriber('source.lfp', server_address = f'{network_location.address}:{network_location.port}')

        def workload(data):
            lfp_data = data['lfp_sub'].receive(timeout=50)
            if lfp_data is not None:
                data['publisher'].send(f'{json.dumps(lfp_data)}')
        
        def cleanup(data):
            pipe_send.close()

        self._proc = fsgui.process.ProcessObject({}, setup, workload, cleanup)
        self._proc.start()

        self.pub_address = pipe_recv.recv()
