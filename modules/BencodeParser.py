class BencodeParser:
    def __init__(self):
        self.data = None
        self.idx = None
        self.find_info_key = None
        self.info_indexes = None
        self.parsing_func = {}
        self._init_parsing_functions()

    def _refresh_state(self, data=None, find_info_key=False):
        self.find_info_key = find_info_key
        self.data = data
        self.info_indexes = None
        self.idx = 0

    def _init_parsing_functions(self):
        for i in range(48, 58):
            self.parsing_func[i] = self._parse_str
        self.parsing_func[100] = self._parse_dict
        self.parsing_func[105] = self._parse_int
        self.parsing_func[108] = self._parse_list

    def parse_data(self, data, find_info_key=False):
        self._refresh_state(data, find_info_key)
        res_dict = self._parse_data()
        if self.find_info_key:
            res = (self.info_indexes[0], self.info_indexes[1], res_dict)
        else:
            res = res_dict
        self._refresh_state()
        return res

    @property
    def _get_cur_byte(self):
        return self.data[self.idx]

    def _parse_data(self):
        return self.parsing_func[self._get_cur_byte]()

    def _parse_int(self):
        self.idx += 1
        str_num = ''
        while self._get_cur_byte in range(48, 58):
            str_num += str(self._get_cur_byte - 48)
            self.idx += 1
        self.idx += 1
        return int(str_num)

    def _parse_str(self):
        cur_str_len = ''
        while self._get_cur_byte in range(48, 58):
            cur_str_len += str(self._get_cur_byte - 48)
            self.idx += 1
        cur_data_len = int(cur_str_len)
        self.idx += 1
        end_idx = self.idx + cur_data_len
        result = self.data[self.idx: self.idx + cur_data_len]
        self.idx = end_idx
        return result

    def _parse_list(self):
        res = []
        self.idx += 1
        while self._get_cur_byte != 101:
            res.append(self.parsing_func[self._get_cur_byte]())
        self.idx += 1
        return res

    def _parse_dict(self):
        res = {}
        begin, end = None, None
        self.idx += 1
        while self._get_cur_byte != 101:
            key = self.parsing_func[self._get_cur_byte]()
            if self.find_info_key and key == b'info':
                begin = self.idx
            value = self.parsing_func[self._get_cur_byte]()
            if self.find_info_key and key == b'info':
                end = self.idx
            res[key] = value
        self.idx += 1
        if self.find_info_key:
            self.info_indexes = (begin, end)
        return res
