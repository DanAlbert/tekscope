import serial
import threading


class Scope(object):
    CHANNEL_A = 'A'
    CHANNEL_B = 'B'

    def __init__(self, port):
        self.com = serial.Serial(
                port=port,
                baudrate=230400,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout = None,
                rtscts=True)

    def start(self):
        self.com.open()

    def stop(self):
        self.com.close()

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

        samples = end_addr / 4
        sample = { Scope.CHANNEL_A: [], Scope.CHANNEL_B: [] }
        for i in range(samples):
            a_high = ord(buf[i * 4])
            a_low = ord(buf[i * 4 + 1])
            b_high = ord(buf[i * 4 + 2])
            b_low = ord(buf[i * 4 + 3])

            a = 256 * a_high + a_low
            b = 256 * b_high + b_low
            sample[Scope.CHANNEL_A].append(a)
            sample[Scope.CHANNEL_B].append(b)
        return sample

    def get_sample(self):
        """Begins, collects and decodes a sample.

        TODO: This function spends a lot of time waiting. Make it asynchronous.
        """
        self.begin_sample()
        end_addr = self.wait_for_sample()
        buf = self.read_memory()
        return self.decode_sample(buf, end_addr)

    def set_big_preamp(self, channel):
        self.command("S P %s" % channel)

    def set_sample_rate_divisor(self, divisor):
        if divisor & ~0xf:
            raise RuntimeError('Invalid sample rate divisor %d' % divisor)
        else:
            # TODO: pretty sure this should be chr(), not str(), but chr()
            #       fails...
            self.command("S R %s" % str(divisor))


class ScopeReadThread(threading.Thread):
    def __init__(self, scope, scope_data):
        super(ScopeReadThread, self).__init__()

        self.scope = scope
        self.scope_data = scope_data
        self.stopped = True

    def run(self):
        self.stopped = False
        self.scope.start()
        while not self.stopped:
            self.scope_data.append(self.scope.get_sample())
        self.scope.stop()

    def stop(self):
        self.stopped = True

    """
    # configure the serial connections (the parameters differs on the device you are connecting to)
    
    channel1data = [0] * 1100        # Create empty array ready to receive result
    channel2data = [0] * 1100        # Create empty array ready to receive result
     
    ser.write("W A 128" + '\r\n')# + str(128) + '\r\n')
    ser.write("W F 0 0 42 241" + '\r\n')# + str(0) + " " + str(0) + " " + str(42) + " " + str(241) + '\r\n')
    """
