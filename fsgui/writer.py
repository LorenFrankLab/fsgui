import h5py
import time
import numpy as np

def generate_filename(tag):
    date = time.localtime()
    date_string = f'{date.tm_year:04d}{date.tm_mon:02d}{date.tm_mday:02d}'
    time_string = f'{date.tm_hour:02d}{date.tm_min:02d}{date.tm_sec:02d}'
    return f'{date_string}-{time_string}_{tag}.h5'

class BufferedHDFWriter:
    def __init__(self, node_id, key, writer, buffer_size):
        self.writer = writer

        self.node_id = node_id
        self.key = key

        self.buffer_size = buffer_size
        self.buffer = np.zeros(shape=(buffer_size,), dtype='double')
        self.index = 0

    def append(self, value):
        self.buffer[self.index] = value
        self.index += 1

        if self.index >= self.buffer_size:
            self.writer.append(self.node_id, self.key, self.buffer)
            self.index = 0

    def flush(self):
        self.writer.append(self.node_id, self.key, self.buffer[:self.index])
        self.index = 0

class HDFWriter:
    def __init__(self, filename):
        self.file = h5py.File(filename, mode='a')
        self.dataset_map = {}
    
    def __get_dataset(self, node_id, key):
        tup = (node_id, key)
        if tup not in self.dataset_map:
            node_group = self.file.require_group(node_id)
            if key in node_group:
                dataset = node_group[key]
            else:
                dataset = node_group.create_dataset(key, shape=(0,), dtype='f', chunks=(256,), maxshape=(None,))
            self.dataset_map[tup] = dataset
        return self.dataset_map[tup]

    def append(self, node_id, key, data):
        dataset = self.__get_dataset(node_id, key)
        data_size = len(data) if hasattr(data, '__len__') else 1

        length, = dataset.shape
        dataset.resize((length+data_size,))

        dataset[length:length+data_size] = data

    def close(self):
        self.file.close()

