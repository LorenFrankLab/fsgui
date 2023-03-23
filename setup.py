import setuptools

setuptools.setup(
    name='fsgui',
    version='0.0.1',
    packages=setuptools.find_packages(),
    install_requires=[
        'oyaml',
        'numpy',
        'zmq',
        'shapely',
        'msgpack',
        'PyQt6',
        'matplotlib',
        'h5py',
        'graphviz',
        'pyqtgraph',
        'pyopengl',
        'scipy',
    ],
)