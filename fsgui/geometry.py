class TrackGeometryLinearizationFile:
    def __init__(self, filename):
        self.filename = filename
        remaining_lines = self.__read_lines(filename)

        self.linearization, remaining_lines = self.__parse_lines(remaining_lines)

    def __read_lines(self, filename):
        with open(filename, 'rb') as f:
            return f.readlines()

    def is_binary_or_empty(self, data):
        if len(data) == 0:
            return True
        # Check for null bytes
        if b'\x00' in data:
            return True

        # Check if there are any non-ASCII characters
        try:
            data.decode('ascii')
        except UnicodeDecodeError:
            return True

        return False

    def __parse_lines(self, lines):
        index = 0 

        line = lines[index].strip()
        if line != b'<Linearization Object> 1':
            raise ValueError(f'Expected linearization object tag, got: {line}')
        index += 1
        line = lines[index].strip()

        while self.is_binary_or_empty(line):
            index += 1
            line = lines[index].strip()

        if line != b'<Linear geometry human readable> 1':
            raise ValueError(f'Expected linear geometry human readable tag, got: {line}')

        index += 1
        line = lines[index].strip()
        if line != b'<Start settings>':
            raise ValueError(f'Expected start settings tag, got: {line}')

        index += 1
        line = lines[index].strip()
        if line != b'Description: Linear geometry':
            raise ValueError(f'Expected description line, got: {line}')

        index += 1
        line = lines[index].strip()

        results = []

        while line == b'<line settings>' and index + 3 < len(lines):
            line_x = lines[index+1].strip()
            line_y = lines[index+2].strip()

            if b'nodes_x' not in line_x:
                raise ValueError(f'Expected nodes_x, got: {line_x}')
            if b'nodes_y' not in line_y:
                raise ValueError(f'Expected nodes_y, got: {line_y}')
        
            start_x, end_x = map(int, line_x.split()[1:])
            start_y, end_y = map(int, line_y.split()[1:])
            results.append({
                'start': (start_x, start_y),
                'end': (end_x, end_y)
            })

            index += 3
            line = lines[index].strip()

        if line != b'<End settings>':
            raise ValueError(f'Expected end settings, got: {line}')
        index += 1

        return results, lines[index:]

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
