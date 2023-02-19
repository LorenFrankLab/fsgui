class TrackGeometry:
    class Zone:
        def __init__(self, zone_id, polygon):
            self.zone_id = zone_id
            self.polygon = polygon

        def __repr__(self):
            return f'(Zone {self.zone_id}: {self.polygon})'

    class Polygon:
        def __init__(self, nodes):
            self.nodes = nodes

        def __repr__(self):
            return f'(Polygon{self.nodes})'

    def __init__(self, linearization, rangeline, zones, inclusion, exclusions):
        self.linearization = linearization
        self.rangeline = rangeline
        self.zones = zones
        self.inclusion = inclusion
        self.exclusions = exclusions
    
    @property
    def get_linearization(self):
        return self.linearization

    @property
    def get_rangeline(self):
        return self.rangeline

    @property
    def get_zones(self):
        return self.zones

    @property
    def get_inclusion_zone(self):
        return self.inclusion

    @property
    def get_exclusion_zone(self):
        return self.exclusions

    def __repr__(self):
        return f'(Geometry (Inclusion: {self.inclusion}))'

class TrackGeometryFileReader:
    class BufferedReader:
        def __init__(self, content):
            self.lines = content.split('\n')
            self.index = -1

        def __advance_index(self):
            self.index += 1
            if self.index < len(self.lines):
                return self.index
            else:
                return None

        def next(self):
            self.__advance_index()
            while self.line is not None and self.line.strip() == '':
                self.__advance_index()
            return self.line

        @property
        def line(self):
            if self.index < len(self.lines):
                return self.lines[self.index]
            else:
                return None
    
    class ParseError(ValueError):
        pass

    def read_file(self, filename):
        with open(filename, 'r') as f:
            content = f.read()
        return self.read_string(content)
    
    def read_string(self, content):
        reader = TrackGeometryFileReader.BufferedReader(content)

        start_tag = '<Start settings>'
        poly_tag = '<polygon settings>'
        end_tag = '<End settings>'

        geometry_data = {
            'linearization': {},
            'rangeline': {},
            'zone': {},
            'inclusion': {},
            'exclusion': {},
        }

        while reader.next():
            if '<Linearization Object>' in reader.line and '1' in reader.line:
                pass
            elif '<Rangeline Object>' in reader.line and '1' in reader.line:
                pass
            elif '<Zone Objects>' in reader.line and '1' in reader.line:
                if start_tag in reader.next():
                    if 'Description: Zone geometry' in reader.next():
                        while poly_tag in reader.next():
                            if 'Zone id:' in reader.next():
                                zone_id = int(reader.line.split(' ')[2])
                            else:
                                raise ParseError
                            if 'nodes_x:' in reader.next():
                                nodes_x = list(map(float, reader.line.split(' ')[1:]))
                            else:
                                raise ParseError
                            if 'nodes_y:' in reader.next():
                                nodes_y = list(map(float, reader.line.split(' ')[1:]))
                            else:
                                raise ParseError

                            geometry_data['zone'][zone_id] = list(zip(nodes_x, nodes_y))
                    else:
                        raise TrackGeometryFileReader.ParseError('Expected description: Zone geometry')

                    if end_tag in reader.line:
                        pass
                    else:
                        raise TrackGeometryFileReader.ParseError(f'Expected end tag, got {reader.line}')
                else:
                    raise TrackGeometryFileReader.ParseError('Expected start tag, got {reader.line}')
            elif '<Inclusion Zone Object>' in reader.line and '1' in reader.line:
                if start_tag in reader.next():
                    if 'Description: Inclusion Zone geometry' in reader.next():
                        while poly_tag in reader.next():
                            if 'Zone id:' in reader.next():
                                # grab the zone id from string (e.g. 'Zone id: 1')
                                zone_id = int(reader.line.split(' ')[2])
                            else:
                                raise ParseError
                            if 'nodes_x:' in reader.next():
                                nodes_x = list(map(float, reader.line.split(' ')[1:]))
                            else:
                                raise ParseError
                            if 'nodes_y:' in reader.next():
                                nodes_y = list(map(float, reader.line.split(' ')[1:]))
                            else:
                                raise ParseError

                            geometry_data['inclusion'][zone_id] = list(zip(nodes_x, nodes_y))
                    else:
                        raise TrackGeometryFileReader.ParseError('Expected description: Zone geometry')
                    if end_tag in reader.line:
                        pass
                    else:
                        raise TrackGeometryFileReader.ParseError(f'Expected end tag, got {reader.line}')
                else:
                    raise TrackGeometryFileReader.ParseError('Expected start tag, got {reader.line}')
 
                pass
            elif '<Exclusion Zone Objects>' in reader.line and '1' in reader.line:
                pass
            else:
                pass

        return geometry_data
