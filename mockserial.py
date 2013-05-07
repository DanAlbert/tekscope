import random
import re
import time

PARITY_NONE = None
STOPBITS_ONE = 1
EIGHTBITS = 8

def low_byte(short):
    return short & 0xff

def high_byte(short):
    return low_byte(short >> 8)

class Serial(object):
    def __init__(self,
            port,
            baudrate,
            parity,
            stopbits,
            bytesize,
            timeout,
            rtscts):
        self.timeout = timeout
        self.sample_period = 1.0 / 20000000.0
        self.out_buf = []
        self.mem_buf = []

    def open(self):
        pass

    def close(self):
        pass

    def read(self, size=1):
        if len(self.out_buf) < size:
            raise RuntimeError('Buffer underflow')
        
        data = self.out_buf[:size]
        self.out_buf = self.out_buf[size:]
        return data

    def write(self, data):
        rate_cmd = re.search('^S R (.)\r\n$', data)
        preamp_cmd = re.search('^S P ([AB])\r\n$', data)
        sample_cmd = re.search('^S G\r\n$', data)
        read_mem_cmd = re.search('^S B\r\n$', data)
        if rate_cmd:
            n = ord(rate_cmd.group(1))
            if n & ~(0xf):
                raise RuntimeError('Invalid divisor %d' % n)
            rate = 20000000.0 / (2 ** n)
            self.sample_period = 1 / rate
        elif preamp_cmd:
            pass
        elif sample_cmd:
            self.begin_sample()
        elif read_mem_cmd:
            self.put_mem_buf()
        else:
            raise NotImplementedError()

    def begin_sample(self):
        min_samples = 1
        max_samples = 1024
        num_samples = random.randrange(min_samples, max_samples + 1)
        self.mem_buf = []

        for _ in range(num_samples):
            sample_a = self.random_sample()
            sample_b = self.random_sample()

            self.mem_buf.append(high_byte(sample_a))
            self.mem_buf.append(low_byte(sample_a))
            self.mem_buf.append(high_byte(sample_b))
            self.mem_buf.append(low_byte(sample_b))

        end_addr = num_samples * 4
        self.out_buf.append('A')
        self.out_buf.append(high_byte(end_addr))
        self.out_buf.append(low_byte(end_addr))

    def put_mem_buf(self):
        self.out_buf.append('D')
        self.out_buf.extend(self.mem_buf)
        self.out_buf.extend([0] * (4096 - len(self.mem_buf)))

    def random_sample(self):
        time.sleep(self.sample_period)
        return random.randrange(0, 0x03ff + 1)
