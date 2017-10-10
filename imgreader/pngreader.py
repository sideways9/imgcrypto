import logging
import os
import struct

import imgreader
from utils import mathutils as mu


class PngChunk(object):
    __PUBLIC = 0
    __PRIVATE = 1

    __CRITICAL = 0
    __ANCILLARY = 1

    __RESERVED_VALID = 0
    __RESERVED_INVALID = 1

    __COPY = 0
    __NO_COPY = 1

    def __init__(self, type, length, data, crc):
        self.type = type
        self.__read_type()
        self.length = length
        self.data = data
        self.chunk_crc = crc
        self.computed_crc = mu.crc(data, 0xedb88320, initial=0xffffffff) ^ 0xffffffffff

    def __read_type(self):
        property_bit = 0b00100000

        self.ancillary_bit = ord(self.type[0]) & property_bit
        self.private_bit = ord(self.type[1]) & property_bit
        self.reserved_bit = ord(self.type[2]) & property_bit
        self.safe_to_copy_bit = ord(self.type[3]) & property_bit

    def __str__(self):
        return "%s: len = %i, chunk_crc = 0x%08x, comp_crc = 0x%08x" % (self.type, self.length, self.chunk_crc, self.computed_crc)


class PngHeaderChunk(PngChunk):
    def __init__(self, type, length, data, crc):
        super().__init__(type, length, data, crc)

        self.parse_data()


    def parse_data(self):
        self.width = struct.unpack(">I", self.data[0:4])[0]
        self.height = struct.unpack(">I", self.data[4:8])[0]
        self.bit_depth = int(self.data[8])
        self.color_type = int(self.data[9])
        self.compression_method = int(self.data[10])
        self.filter_method = int(self.data[11])
        self.interlace_method = int(self.data[12])

    def __str__(self):
        s = '%s\nw: %i, h: %i %i%i%i%i' % (
            super().__str__(),
            self.width,
            self.height,
            1 if self.ancillary_bit else 0,
            1 if self.private_bit else 0,
            1 if self.reserved_bit else 0,
            1 if self.safe_to_copy_bit else 0
        )

        return s

        return '%s\nw: %i, h: %i' % (s, self.width, self.height)

class ChunkFactory(object):
    __CHUNK_MAP__ = {
        'IHDR': PngHeaderChunk
    }

    @staticmethod
    def make_chunk(type, length, data, crc):
        chunk_class = ChunkFactory.__CHUNK_MAP__[str.upper(type)]
        return chunk_class(type, length, data, crc)


class PngReader(object):
    SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10]

    """
        Inits the object
        :rtype: str
        """
    def __init__(self, file: str) -> None:
        try:
            with open(file, 'rb') as openfile:
                self.contents = openfile.read()
        except IOError:
            self.contents = ''

    def parse_signature(self, rem_contents):
        try:
            content_signature = rem_contents[0:len(self.SIGNATURE)]

            match = True
            for i in range(0,len(self.SIGNATURE)):
                if content_signature[i] != self.SIGNATURE[i]:
                    match = False
                    break

            if match:
                return rem_contents[len(self.SIGNATURE):]

        except:
            logging.error("Exception in parse_signature")
            return None

        return None

    def parse_length(self, rem_contents):
        return struct.unpack(">I", rem_contents[0:4])[0], rem_contents[4:]

    def parse_chunk_type(self, rem_contents):
        return rem_contents[0:4].decode('utf-8'), rem_contents[4:]

    def parse_chunk_data(self, rem_contents, length):
        return rem_contents[0:length], rem_contents[length:]

    def parse_crc(self, rem_contents):
        return struct.unpack(">I", rem_contents[0:4])[0], rem_contents[4:]

    def parse_chunk(self, rem_contents):
        (length, rem_contents) = self.parse_length(rem_contents)
        (chunk_type, rem_contents) = self.parse_chunk_type(rem_contents)
        (chunk_data, rem_contents) = self.parse_chunk_data(rem_contents, length)
        (crc, rem_contents) = self.parse_crc(rem_contents)

        return ChunkFactory.make_chunk(chunk_type, length, chunk_data, crc), rem_contents

    def parse(self):
        rem_content = self.parse_signature(self.contents)
        self.chunks = []
        while len(rem_content) > 0:
            (chunk, rem_content) = self.parse_chunk(rem_content)
            self.chunks.append(chunk)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    reader = PngReader(os.path.join(imgreader.RESOURCES, 'testfile'))
    reader.parse()

    for chunk in reader.chunks:
        logging.info(str(chunk))
