import serial
import threading


class Control(object):
    def __init__(self, control_id, update_callback):
        self.control_id = control_id
        self.update_callback = update_callback


class Encoder(Control):
    def __init__(self, update_callback):
        super(Encoder, self).__init__(update_callback)
        self.value = 0

    def update(self, modifier):
        self.value += modifier
        self.update_callback(self.value)


class Switch(Control):
    def __init__(self, update_callback):
        super(Switch, self).__init__(update_callback)
        self.value = False

    def update(self, state):
        self.value = state
        self.update_callback(self.value)


class Led(object):
    def __init__(self, com, control_id):
        self.com = com
        self.control_id = control_id

    def update(self, value):
        self.com.write('%s%d' % (str(self.control_id), int(value)))


class ControlPanel(object):
    BAUD_RATE = 115200

    def __init__(self, port):
        self.com = serial.Serial(
                port=port,
                baud=ControlPanel.BAUD_RATE,
                timeout=None)
        self.encoders = {}
        self.switches = {}
        self.leds = {}

    def add_encoder(self, encoder):
        if encoder.control_id in self.encoders:
            raise RuntimeError(
                    'Encoder %s was already added to the control panel' %
                    str(encoder.control_id))
        self.encoders[encoder.control_id] = encoder

    def add_switch(self, switch):
        if switch.control_id in self.switches:
            raise RuntimeError(
                    'Switch %s was already added to the control panel' %
                    str(switch.control_id))
        self.switches[switch.control_id] = switch

    def add_led(self, led):
        if led.control_id in self.leds:
            raise RuntimeError(
                    'LED %s was already added to the control panel' %
                    str(led.control_id))
        self.leds[led.control_id] = led

    def update_led(self, led_id, value):
        self.leds[led_id].update(value)

    def update(self):
        self.handle_message(self.com.read(2))

    def is_encoder_message(self, message):
        return message[0].isdigit() and message.length() == 2

    def is_switch_message(self, message):
        return message[0].isupper() and message.length() == 2

    def handle_message(self, message):
        if self.is_encoder_message(message):
            self.handle_encoder(message)
        elif self.is_switch_message(message):
            self.handle_switch(message)
        else:
            raise NotImplementedError('unhandled message %s' % message)

    def handle_encoder(self, message):
        encoder_id = int(message[0])
        if encoder_id not in self.encoders:
            raise RuntimeError(
                    'message received for unhandled encoder %s' %
                    str(encoder_id))

        encoder = self.encoders[encoder_id]
        step = 1
        if message[1] == 'L':
            encoder.update(-step)
        elif message[1] == 'R':
            encoder.update(step)
        else:
            raise RuntimeError('malformed encoder message %s' % message)

    def handle_switch(self, message):
        switch_id = message[0]
        if switch_id not in self.switches:
            raise RuntimeError(
                    'message received for unhandled switch %s' %
                    str(switch_id))

        switch = self.switches[switch_id]
        if message[1] == '1':
            switch.update(True)
        elif message[1] == '0':
            switch.update(False)
        else:
            raise RuntimeError('malformed switch message %s' % message)


class ControlPanelThread(threading.Thread):
    def __init__(self, control_panel):
        super(ControlPanelThread, self).__init__()
        self.control_panel = control_panel
        self.stopped = True

    def run(self):
        self.stopped = False
        while not self.stopped:
            self.control_panel.update()

    def stop(self):
        self.stopped = True
