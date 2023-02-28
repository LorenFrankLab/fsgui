import multiprocessing as mp
import fsgui.process
import fsgui.node
import fsgui.spikegadgets.trodes
import logging
import fsgui.spikegadgets.trodesnetwork as trodesnetwork
import fsgui.network
import time
import numpy as np
 
class LinearizedBinnedCameraType(fsgui.node.NodeTypeObject):
    def __init__(self, type_id, network_location):
        name = 'Linearized binned Trodes camera'
        super().__init__(
            type_id=type_id,
            node_class='source',
            name=name,
            datatype='bin_id',
            default= {
                'type_id': type_id,
                'instance_id': '',
                'nickname': name,
                'track_linearization': None,
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
            {
                'label': 'Track linearization',
                'name': 'track_linearization',
                'type': 'linearization',
                'default': config['track_linearization'],
                'tooltip': 'This is the scheme to linearize the track',
            }
        ]
    
    def build(self, config, addr_map):
        try:
            trodesnetwork.SourceSubscriber('source.position', server_address = f'{self.network_location.address}:{self.network_location.port}')
        except Exception:
            raise ValueError('Could not connect to Trodes camera')

        segment_dictionary = { segment_id: {'bounds': segment, 'bin_count': max(segment) - min(segment) + 1} for segment_id, segment in enumerate(config['track_linearization']['segments']) }
        max_bin_size = max([max(value['bounds']) for value in segment_dictionary.values()])
        total_bins = max_bin_size + 1

        def setup(logging, data):
            data['camera_sub'] = trodesnetwork.SourceSubscriber('source.position', server_address = f'{self.network_location.address}:{self.network_location.port}')
            data['receive_none_counter'] = 0

        def workload(connection, publisher, reporter, data):
            t0 = time.time()

            camera_data = data['camera_sub'].receive(timeout=50)
            if camera_data is None:
                data['receive_none_counter'] += 1
                if data['receive_none_counter'] > 40 and data['receive_none_counter'] % 40 == 0:
                    connection.info(f'Camera source has not received any camera data from Trodes in a while...')
            if camera_data is not None:
                data['receive_none_counter'] = 0

                bin_value = 2

                t1 = time.time()

                segment_id = camera_data['lineSegment']
                segment = segment_dictionary[segment_id]

                relative_distance = camera_data['posOnSegment']
                if int(relative_distance) == 1:
                    relative_distance -= 1e-7

                bins_distance = int(relative_distance * segment['bin_count'])

                if segment['bounds'][0] == min(segment['bounds']):
                    bin_value = bins_distance + min(segment['bounds'])
                elif segment['bounds'][0] == max(segment['bounds']):
                    bin_value = max(segment) - bins_distance

                publisher.send(bin_value)
                reporter.send({
                    'bin_value': np.bincount([bin_value], minlength=total_bins).tolist(),
                })

                t2 = time.time()
                print(f'{t1-t0:.6f} {t2-t1:.6f}')

                print(bin_value)

        return fsgui.process.build_process_object(setup, workload)
        