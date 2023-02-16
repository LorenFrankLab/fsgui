import numpy as np

class CircularArray:
    """
    Slice view goes forward.
    Placing moves backward.
    """
    def __init__(self, length, dtype=None):
        self.length = length
        self.array = np.zeros((self.length,), dtype=dtype)
        self.index = 0

        assert length > 0

    def place(self, x):
        self.index -= 1
        self.index %= self.length
        self.array[self.index] = x

    @property
    def get_slice(self):
        return np.roll(self.array, -self.index)

class ArrayList:
    def __init__(self, width, capacity=10000, dtype=None):
        self.array = np.zeros(shape=(capacity, width), dtype=dtype)
        self.index = 0 
    
    def place(self, x):
        if self.index >= self.array.shape[0]:
            self.array = np.vstack((self.array, np.zeros_like(self.array)))
        self.array[self.index, :] = x
        self.index += 1

    def get_slice(self):
        return self.array[:self.index,:]