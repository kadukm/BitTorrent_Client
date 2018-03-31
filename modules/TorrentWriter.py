import os
import math
import struct


class TorrentWriter:
    def __init__(self, metainfo):
        self.metainfo = metainfo
        self._downloads_dir = os.path.join(os.getcwd(), 'downloads')
        self._checkpoint_path = os.path.join(os.getcwd(), '.torrents_info',
                                            self.metainfo.info_hash2str)
        self.check_place_to_download()
        self.check_checkpoint_path()

    @property
    def downloads_dir(self):
        return self._downloads_dir

    @property
    def checkpoint_path(self):
        return self._checkpoint_path

    def get_uncompleted_piece_indexes(self):
        res = []
        with open(self.checkpoint_path, 'rb') as f:
            data = f.read()
            pieces_exist = self.get_info_about_pieced_from_bytes(data)
        for i in range(len(self.metainfo.pieces)):
            if not pieces_exist[i]:
                res.append(i)
        return res

    @staticmethod
    def get_info_about_pieced_from_bytes(data):
        def bits_in_byte(cur_byte):
            str_byte = bin(cur_byte)[2:]
            str_byte = '0'*(8 - len(str_byte)) + str_byte
            for str_bit in str_byte:
                yield str_bit == '1'
        res = []
        for byte in data:
            for bit in bits_in_byte(byte):
                res.append(bit)
        return res

    def check_place_to_download(self):
        path_to_place = os.path.join(self.downloads_dir, self.metainfo.name)
        if not os.path.exists(path_to_place):
            self.create_place_to_download()

    def check_checkpoint_path(self):
        dot_torrents_info_dir = os.path.split(self.checkpoint_path)[0]
        if not os.path.exists(dot_torrents_info_dir):
            os.makedirs(dot_torrents_info_dir)
        if not os.path.exists(self.checkpoint_path):
            self.create_checkpoint()

    def write_piece(self, piece_idx, piece):
        piece_offset_in_data = piece_idx * self.metainfo.piece_length
        if self.metainfo.is_single_file:
            self._write_data_in_single_file(
                os.path.join(self.downloads_dir, self.metainfo.name),
                piece_offset_in_data, 0, len(piece), piece)
        else:
            file_offset_in_data = 0
            file_idx = -1
            next_offset = 0
            while next_offset <= piece_offset_in_data:
                file_idx += 1
                file_offset_in_data = next_offset
                next_offset += self.metainfo.files[file_idx]['length']

            offset_in_piece = 0
            while offset_in_piece != len(piece):
                offset_in_file = 0
                file_len = self.metainfo.files[file_idx]['length']
                file_path = self.metainfo.files[file_idx]['path']
                full_path = os.path.join(
                    self.downloads_dir, self.metainfo.name, file_path)
                if file_offset_in_data < piece_offset_in_data:
                    offset_in_file = piece_offset_in_data - file_offset_in_data
                    data_len = min(len(piece), file_len - offset_in_file)
                else:
                    data_len = min(file_len, len(piece) - offset_in_piece)

                self._write_data_in_single_file(
                    full_path, offset_in_file, offset_in_piece,
                    data_len, piece)
                offset_in_piece += data_len
                file_offset_in_data += file_len
                file_idx += 1
        self._upd_checkpoint(piece_idx)

    def _upd_checkpoint(self, piece_idx):
        byte_idx = int(piece_idx / 8)
        with open(self.checkpoint_path, 'r+b') as f:
            f.seek(byte_idx)
            cur_byte = f.read(1)
            cur_int_byte = struct.unpack('@B', cur_byte)[0]
            bit_idx_in_byte = piece_idx % 8
            cur_int_byte |= 2 ** (7 - bit_idx_in_byte)
            cur_byte = struct.pack('@B', cur_int_byte)
            f.seek(byte_idx)
            f.write(cur_byte)

    @staticmethod
    def _write_data_in_single_file(
            file_path, offset_in_file, offset_in_piece, data_len, piece):
        with open(file_path, 'r+b') as f:
            f.seek(offset_in_file)
            f.write(piece[offset_in_piece: offset_in_piece + data_len])

    def create_checkpoint(self):
        file_len = math.ceil(len(self.metainfo.pieces) / 8)
        self._create_empty_file(self.checkpoint_path, file_len)

    def create_place_to_download(self):
        if self.metainfo.is_single_file:
            self._create_single_empty_file(file_path=self.metainfo.name,
                                           length=self.metainfo.length)
        else:
            self._create_empty_files()

    def _create_single_empty_file(self, file_path, length):
        full_path = os.path.join(self.downloads_dir, file_path)
        dirs_path, _ = os.path.split(full_path)
        os.makedirs(dirs_path, exist_ok=True)
        self._create_empty_file(full_path, length)

    def _create_empty_files(self):
        base_dir = self.metainfo.name
        for file_dict in self.metainfo.files:
            file_path = os.path.join(base_dir, file_dict['path'])
            self._create_single_empty_file(file_path, file_dict['length'])

    @staticmethod
    def _create_empty_file(file_path, length):
        with open(file_path, 'wb') as f:
            f.seek(length - 1)
            f.write(b'\x00')
