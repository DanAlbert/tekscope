import random
import threading
import time

class ScopeThread(threading.Thread):
    def __init__(self, scope_data):
        super(ScopeThread, self).__init__()
        self.scope_data = scope_data
        self.stopped = True

    def run(self):
        self.stopped = False
        while not self.stopped:
            self.scope_data.append(random.randrange(-5, 5))
            time.sleep(1)

    def stop(self):
        self.stopped = True

    """
    # configure the serial connections (the parameters differs on the device you are connecting to)
    ser = serial.Serial(
        port="COM122",
        baudrate=230400,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout = 10,
        rtscts=True
        )

    ser.close()
    ser.open()
    ser.isOpen()
    
    channel1data = [0] * 1100        # Create empty array ready to receive result
    channel2data = [0] * 1100        # Create empty array ready to receive result
     
    ser.write("W A 128" + '\r\n')# + str(128) + '\r\n')
    ser.write("W F 0 0 42 241" + '\r\n')# + str(0) + " " + str(0) + " " + str(42) + " " + str(241) + '\r\n')
    ser.write("S R " + str(0b00000111) + '\r\n') #Sets Sample rate to 20MSamp/s / 2^7 = 156uS
    ser.write("S P A" + '\r\n') #Sets channel A to Big preamp
    ser.write("S P B" + '\r\n') #Sets channel B to Big preamp
    """
