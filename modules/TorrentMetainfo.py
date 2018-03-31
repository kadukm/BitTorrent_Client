import hashlib
import os

from .BencodeParser import BencodeParser


class TorrentMetainfo:
    def __init__(self, filename):
        self.info_hash = None
        self.info_hash2str = None
        self.name = None
        self.length = None
        self.announce_list = []
        self.piece_length = None
        self.pieces = None
        self.is_single_file = True
        self.files = None
        self._parse_torrent_file(filename)

    def get_piece_len_at(self, piece_idx):
        return (self.piece_length if piece_idx < len(self.pieces) - 1
                else self.length - (len(self.pieces) - 1) * self.piece_length)

    @staticmethod
    def _get_data_from(filename):
        with open(filename, 'rb') as f:
            data = f.read()
        return data

    def _parse_torrent_file(self, filename):
        data = self._get_data_from(filename)
        bp = BencodeParser()
        begin, end, meta_dict = bp.parse_data(data, find_info_key=True)
        sha1_hash = hashlib.sha1(data[begin: end])
        self.info_hash = sha1_hash.digest()
        self.info_hash2str = sha1_hash.hexdigest()
        self.announce_list.append(meta_dict[b'announce'].decode())
        if b'announce-list' in meta_dict:
            self._add_announces(meta_dict[b'announce-list'])
        self._decode_info(meta_dict[b'info'])

    def _add_announces(self, announces):
            for cur_ann_list in announces:
                for bin_announce in cur_ann_list:
                    str_announce = bin_announce.decode()
                    if self.announce_list[0] != str_announce:
                        self.announce_list.append(str_announce)

    def _decode_info(self, info):
        self.name = info[b'name'].decode()
        self.piece_length = info[b'piece length']
        pieces = info[b'pieces']
        self.pieces = [pieces[i:i+20] for i in range(0, len(pieces), 20)]
        if b'files' in info:
            self.is_single_file = False
            self.files = []
            for file in info[b'files']:
                path_segments = [v.decode('utf-8') for v in file[b'path']]
                self.files.append({
                    'length': file[b'length'],
                    'path': os.path.join(*path_segments)
                })
            self.length = sum(file['length'] for file in self.files)
        else:
            self.length = info[b'length']
