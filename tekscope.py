"""Backend service for the TekBots USB oscilloscope.

Authors:
    Dan Albert <dan@gingerhq.net>
    Aidan Daly-Jensen

Developer documentation:
    Encoder controls send 1R for 1 tick right and 1L for one tick left.
    Button status is indicated by AD (for button A down)
    To turn on light A, send AO

    The service needs to allow the scope front end to reconnect at any time.
    Since we simply maintain a client list, this isn't a problem.

    The controller (I assume Don is referring to the controller attached to the
    control console and not the scope) turns off occasionally, so don't expect
    to always see data on that channel.

    Scope output:
    A sample is started with "S G\r\n"
    When the sample is complete, the score will respond with "A HI LO" with A
    signally that the sample is complete, and HI and LO forming a 10-bit
    address of the sample in the scope's buffer.

    The buffer can be accessed with "S B\r\n"
    The scope will respond with the entire scope memory (4KB) and one
    additional byte (packet is preceded by 'D'). The buffer format returned is
    A1a1B1b1C1c1 where A1 and a1 make the first 10-bit sample value, B1 and b1
    make the second 10-bit sample value, and so on.

    Application organization:

    Communication with the scope should be done in a separate process, as
    either application crashing should not kill the other. The scope process
    can communicate with the service with a socket, a pipe or shared memory.

    Communication with the controls should follow a similar paradigm. A
    separate process can post to the web service whenever control information
    needs to be updated.
"""
import json
import signal
import sys
from twisted.internet import reactor, protocol

from controls import ControlPanel, ControlPanelThread, Encoder, Switch, Led
from scope import Scope, ScopeReadThread


class ScopeProtocol(protocol.Protocol):
    def __init__(self, client_list, scope, control_panel):
        self.client_list = client_list
        self.scope = scope
        self.control_panel = control_panel
        self.pending_data = ''

    def connectionMade(self):
        print "connection from: %s" % self.transport.getPeer()
        self.client_list.add(self)

    def connectionLost(self, reason):
        self.client_list.remove(self)

    def dataReceived(self, data):
        print 'received: %s' % data
        self.pending_data += data
        self.process_data()

    def get_packet(self):
        # TODO: this isn't working quite right...
        if self.pending_data[:1] != '{':
            raise RuntimeError('bad data in buffer: %s' % self.pending_data)
        stack = ['{']
        for i, char in enumerate(self.pending_data[1:]):
            if char == '{':
                stack.append(char)
            elif char == '}' and len(stack) > 0:
                stack.pop()
            elif char == '}' and len(stack) == 0:
                return None

            if len(stack) == 0:
                packet = self.pending_data[:i + 1]
                self.pending_data = self.pending_data[i + 1:]
                return packet
        return None

    def process_data(self):
        #packet = self.get_packet()
        packet = self.pending_data
        self.pending_data = ''
        if not packet:
            return

        data = json.loads(packet)
        for key, value in data.items():
            if key == 'led':
                self.control_panel.update_led(value['id'], value['value'])
            elif key == 'trigger-level':
                self.scope.set_trigger_level(value)
            elif key == 'sample-rate':
                self.scope.set_sample_rate_divisor(value)
            else:
                print 'unhandled message: %s' % data


class ScopeFactory(protocol.Factory):
    def __init__(self, client_list, scope, control_panel):
        self.client_list = client_list
        self.scope = scope
        self.control_panel = control_panel

    def buildProtocol(self, addr):
        return ScopeProtocol(self.client_list, self.scope, self.control_panel)


class ScopeDataSender(object):
    def __init__(self, client_list):
        self.client_list = client_list

    def append(self, data):
        for client in self.client_list:
            client.transport.write('%s\n' % json.dumps(data))

    def send_ui_param(self, name, data):
        client_data = {name: data}
        for client in self.client_list:
            client.transport.write('%s\n' % json.dumps(client_data))


def make_control_panel(port, scope, data_sender):
    control_panel = ControlPanel(port=port)

    def update_encoder_ui_param(control):
        data = {
            'id': '%d' % control.control_id,
            'value': control.value,
        }
        data_sender.send_ui_param('encoder', data)

    def update_switch_ui_param(control):
        data = {
            'id': control.control_id,
            'value': control.value,
        }
        data_sender.send_ui_param('switch', data)

    def update_sample_rate(encoder):
        encoder.value = max(0, min(encoder.value, 15))
        scope.set_sample_rate_divisor(encoder.value)
        data_sender.send_ui_param('sample-rate', scope.sample_rate_divisor)
        update_encoder_ui_param(encoder)

    def update_trigger_level(encoder):
        # TODO: tune these
        trigger_limit = 200
        trigger_step = 1
        encoder.value = max(-trigger_limit, min(encoder.value, trigger_limit))
        scope.set_trigger_level(encoder.value * trigger_step)
        data_sender.send_ui_param('trigger-level', scope.trigger_level)
        update_encoder_ui_param(encoder)

    def toggle_led(switch):
        update_switch_ui_param(switch)
        if switch.value:
            control_panel.toggle_led(switch.control_id)

    control_panel.add_encoder(1, update_encoder_ui_param)
    control_panel.add_encoder(2, update_encoder_ui_param)
    control_panel.add_encoder(3, update_encoder_ui_param)
    control_panel.add_encoder(4, update_encoder_ui_param)
    control_panel.add_encoder(5, update_encoder_ui_param)
    control_panel.add_encoder(6, update_sample_rate, value=7)
    control_panel.add_encoder(7, update_trigger_level, value=0)

    control_panel.add_switch('A', toggle_led)
    control_panel.add_switch('B', toggle_led)
    control_panel.add_switch('C', toggle_led)
    control_panel.add_switch('D', toggle_led)
    control_panel.add_switch('E', toggle_led)
    control_panel.add_switch('F', update_switch_ui_param)
    control_panel.add_switch('G', update_switch_ui_param)
    control_panel.add_switch('H', update_switch_ui_param)
    control_panel.add_switch('I', update_switch_ui_param)
    control_panel.add_switch('J', update_switch_ui_param)
    control_panel.add_switch('P', toggle_led)

    control_panel.add_led('A')
    control_panel.add_led('B')
    control_panel.add_led('C')
    control_panel.add_led('D')
    control_panel.add_led('E')
    control_panel.add_led('P')

    return control_panel


def main():
    server_port = 15151
    client_list = set()

    argc = len(sys.argv)
    if argc < 3 or argc > 4:
        usage()
        sys.exit(-1)

    scope_port = sys.argv[1]
    controls_port = sys.argv[2]

    if argc == 4:
        server_port = int(sys.argv[3])

    scope = Scope(scope_port)
    scope.set_preamp(Scope.CHANNEL_A, high=True)
    scope.set_preamp(Scope.CHANNEL_B, high=True)
    #scope.set_sample_rate_divisor(0x7)
    #scope.set_trigger_level(1.0)  # default trigger at 1v

    data_sender = ScopeDataSender(client_list)

    control_panel = make_control_panel(controls_port, scope, data_sender)

    scope_read_thread = ScopeReadThread(scope, data_sender)
    control_panel_thread = ControlPanelThread(control_panel)

    def stop_server_and_exit(signum, frame):
        print '\rStopping server'
        scope_read_thread.stop()
        control_panel_thread.stop()
        print 'Joining control panel thread...'
        control_panel_thread.join()
        print 'Joining scope read thread... ',
        print 'If this takes too long, kill with ^\\'
        scope_read_thread.join()
        reactor.stop()

    def status_message(msg):
        print msg

    signal.signal(signal.SIGINT, stop_server_and_exit)
    scope_read_thread.start()
    control_panel_thread.start()

    scope_factory = ScopeFactory(client_list, scope, control_panel)
    reactor.listenTCP(server_port, scope_factory)
    reactor.callWhenRunning(
            status_message, 'Server started on port %d' % server_port)
    reactor.run()


def usage():
    print 'usage: python tekscope.py SCOPE_PORT CONTROLS_PORT [SERVER_PORT]'


if __name__ == "__main__":
    main()
