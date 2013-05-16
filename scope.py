import serial
import threading


def low_byte(short):
    return short & 0xff


def high_byte(short):
    return low_byte(short >> 8)


def split_bytes(short):
    return (high_byte(short), low_byte(short))


class Scope(object):
    CHANNEL_A = 'A'
    CHANNEL_B = 'B'
    EXTERNAL = 'EXT'

    RISING_EDGE = 0
    FALLING_EDGE = 1

    def __init__(self, port):
        self.com = serial.Serial(
                port=port,
                baudrate=230400,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=None,
                rtscts=True)

        self.gain = 1  # TODO: this can change, but it isn't clear how...
        self.trigger_channel = Scope.CHANNEL_A
        self.trigger_edge = Scope.RISING_EDGE

        self.set_sample_rate_divisor(0)
        self.set_preamp(Scope.CHANNEL_A, high=True)
        self.set_preamp(Scope.CHANNEL_B, high=True)
        self.set_trigger_level(0.0)
        self.set_trigger_type(edge=Scope.RISING_EDGE, channel=Scope.CHANNEL_A)

    @property
    def sample_rate(self):
        return 20000000.0 / (2 ** self.sample_rate_divisor)

    @property
    def control_register(self):
        reg = self.sample_rate_divisor
        if self.trigger_channel == Scope.CHANNEL_B:
            reg |= 1 << 4
        elif self.trigger_channel == Scope.EXTERNAL:
            reg |= 1 << 6

        if self.trigger_edge == Scope.RISING_EDGE:
            reg |= 1 << 5
        return reg

    def command(self, cmd):
        self.com.write('%s\r\n' % cmd)

    def handle_message(self, msg):
        hex_msg = ["%x" % ord(c) for c in msg]
        raise NotImplementedError('Unhandled message ', hex_msg)

    def begin_sample(self):
        self.command("S G")

    def wait_for_sample(self):
        msg = self.com.read(3)
        while msg[0] != 'A':
            self.handle_message(msg)
            msg = self.com.read(3)
        else:
            upper = ord(msg[1])
            lower = ord(msg[2])
            return 256 * upper + lower

    def read_memory(self):
        self.command("S B")
        msg = self.com.read()
        while msg[0] != 'D':
            self.handle_message(msg)
            msg = self.com.read()
        return self.com.read(4096)

    def decode_sample(self, buf, end_addr):
        if len(buf) != 4096:
            raise RuntimeError('Invalid buffer size')

        sample = {Scope.CHANNEL_A: [], Scope.CHANNEL_B: []}
        for i in range(1024):
            index = ((i + end_addr) * 4) + 4
            a_high = ord(buf[index % 4096])
            a_low = ord(buf[(index + 1) % 4096])
            b_high = ord(buf[(index + 2) % 4096])
            b_low = ord(buf[(index + 3) % 4096])

            a = 256 * a_high + a_low
            b = 256 * b_high + b_low
            a_voltage = (511 - a) * self.ad_step_size
            b_voltage = (511 - b) * self.ad_step_size
            sample[Scope.CHANNEL_A].append(round(a_voltage, 2))
            sample[Scope.CHANNEL_B].append(round(b_voltage, 2))
        return sample

    def get_sample(self):
        """Begins, collects and decodes a sample.

        TODO: This function spends a lot of time waiting. Make it asynchronous.
        """
        self.begin_sample()
        end_addr = self.wait_for_sample()
        buf = self.read_memory()
        return self.decode_sample(buf, end_addr)

    def set_preamp(self, channel, high):
        if high:
            self.ad_step_size = 0.0521
            self.command("S P %s" % channel.upper())
        else:
            self.ad_step_size = 0.00592
            self.command("S P %s" % channel.lower())

    def set_sample_rate_divisor(self, divisor):
        if divisor & ~0xf:
            raise RuntimeError('Invalid sample rate divisor %d' % divisor)
        else:
            self.sample_rate_divisor = divisor
            self.command("S R %d" % self.control_register)

    def set_trigger_type(self, edge, channel):
        self.trigger_edge = edge
        self.trigger_channel = channel
        self.command("S R %d" % self.control_register)

    def set_trigger_level(self, voltage):
        self.trigger_level = voltage
        value = int(511 - self.gain * self.trigger_level / 0.52421484375)
        (high_byte, low_byte) = split_bytes(value)
        self.command("S T %d %d" % (high_byte, low_byte))


class ScopeReadThread(threading.Thread):
    def __init__(self, scope, scope_data):
        super(ScopeReadThread, self).__init__()

        self.scope = scope
        self.scope_data = scope_data
        self.stopped = True

    def run(self):
        self.stopped = False
        while not self.stopped:
            self.scope_data.append(self.scope.get_sample())

    def stop(self):
        self.stopped = True
