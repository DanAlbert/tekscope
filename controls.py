import serial
import threading


class Control(object):
    def __init__(self, control_id, update_callback):
        self.control_id = control_id
        self.update_callback = update_callback


class Encoder(Control):
    def __init__(self, control_id, update_callback, control_panel):
        super(Encoder, self).__init__(control_id, update_callback)
        self.control_panel = control_panel
        self.value = 0

    def update(self, modifier):
        self.value += modifier
        self.update_callback(self)


class Switch(Control):
    def __init__(self, control_id, update_callback, control_panel):
        super(Switch, self).__init__(control_id, update_callback)
        self.control_panel = control_panel
        self.value = False

    def update(self, state):
        self.value = state
        self.update_callback(self)


class Led(object):
    def __init__(self, control_id, com):
        self.com = com
        self.control_id = control_id
        self.value = False

    def update(self, value):
        self.value = value
        self.com.write('%s%d' % (str(self.control_id), int(self.value)))


class ControlPanel(object):
    BAUD_RATE = 9600

    def __init__(self, port):
        self.com = serial.Serial(
                port=port,
                baudrate=ControlPanel.BAUD_RATE,
                timeout=0.2)
        self.encoders = {}
        self.switches = {}
        self.leds = {}

    def stop(self):
        self.com.close()

    def add_encoder(self, encoder_id, encoder_callback):
        encoder = Encoder(encoder_id, encoder_callback, self)
        if encoder.control_id in self.encoders:
            raise RuntimeError(
                    'Encoder %s was already added to the control panel' %
                    str(encoder.control_id))
        self.encoders[encoder.control_id] = encoder

    def add_switch(self, switch_id, switch_callback):
        switch = Switch(switch_id, switch_callback, self)
        if switch.control_id in self.switches:
            raise RuntimeError(
                    'Switch %s was already added to the control panel' %
                    str(switch.control_id))
        self.switches[switch.control_id] = switch

    def add_led(self, led_id):
        led = Led(led_id, self.com)
        if led.control_id in self.leds:
            raise RuntimeError(
                    'LED %s was already added to the control panel' %
                    str(led.control_id))
        self.leds[led.control_id] = led

    def toggle_led(self, led_id):
        self.update_led(led_id, not self.leds[led_id].value)

    def update_led(self, led_id, value):
        self.leds[led_id].update(value)

    def update(self):
        self.handle_message(self.com.read(2))

    def is_encoder_message(self, message):
        return message[0].isdigit() and len(message) == 2

    def is_switch_message(self, message):
        return message[0].isupper() and len(message) == 2

    def handle_message(self, message):
        if len(message) == 0:
            pass  # timed out
        elif self.is_encoder_message(message):
            self.handle_encoder(message)
        elif self.is_switch_message(message):
            self.handle_switch(message)
        else:
            vals = [str(ord(c)) for c in message]
            hex_message = ' '.join(vals)
            raise NotImplementedError('unhandled message %s' % hex_message)

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
        self.control_panel.stop()
