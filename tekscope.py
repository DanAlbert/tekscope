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
    def __init__(self, client_list):
        self.client_list = client_list

    def connectionMade(self):
        print "connection from: %s" % self.transport.getPeer()
        self.client_list.add(self)

    def connectionLost(self, reason):
        self.client_list.remove(self)

    def dataReceived(self, data):
        pass  # TODO: process request


class ScopeFactory(protocol.Factory):
    def __init__(self, client_list):
        self.client_list = client_list

    def buildProtocol(self, addr):
        return ScopeProtocol(self.client_list)


class ScopeDataSender(object):
    def __init__(self, client_list):
        self.client_list = client_list

    def append(self, data):
        for client in self.client_list:
            client.transport.write(json.dumps(data))


def make_control_panel(port):
    control_panel = ControlPanel(port=port)

    def update_position(encoder, scope, control_panel):
        pass

    def update_scale(encoder, scope, control_panel):
        pass

    def no_action(encoder, scope, control_panel):
        pass

    def toggle_led(switch, scope, control_panel):
        control_panel.update_led(switch.control_id, switch.value)

    control_panel.add_encoder(Encoder(1, update_position))
    control_panel.add_encoder(Encoder(2, update_scale))
    control_panel.add_encoder(Encoder(3, update_position))
    control_panel.add_encoder(Encoder(4, update_scale))
    control_panel.add_encoder(Encoder(5, update_position))
    control_panel.add_encoder(Encoder(6, update_scale))
    control_panel.add_encoder(Encoder(7, no_action))

    control_panel.add_switch(Switch('A', toggle_led))
    control_panel.add_switch(Switch('B', toggle_led))
    control_panel.add_switch(Switch('C', toggle_led))
    control_panel.add_switch(Switch('D', toggle_led))
    control_panel.add_switch(Switch('E', toggle_led))
    control_panel.add_switch(Switch('G', toggle_led))
    control_panel.add_switch(Switch('H', toggle_led))
    control_panel.add_switch(Switch('I', toggle_led))
    control_panel.add_switch(Switch('J', toggle_led))
    control_panel.add_switch(Switch('P', toggle_led))

    control_panel.add_led(Led('A'))
    control_panel.add_led(Led('B'))
    control_panel.add_led(Led('C'))
    control_panel.add_led(Led('D'))
    control_panel.add_led(Led('E'))
    control_panel.add_led(Led('G'))
    control_panel.add_led(Led('H'))
    control_panel.add_led(Led('I'))
    control_panel.add_led(Led('J'))
    control_panel.add_led(Led('P'))

    return control_panel


def main():
    server_port = 5000
    client_list = set()

    argc = len(sys.argv)
    if argc < 3 or argc > 4:
        usage()
        sys.exit(-1)

    scope_port = sys.argv[1]
    controls_port = sys.argv[2]

    if argc == 4:
        server_port = int(sys.argv[3])

    control_panel = make_control_panel(controls_port)
    control_panel_thread = ControlPanelThread(control_panel)

    data_sender = ScopeDataSender(client_list)
    scope = Scope(scope_port)
    scope.set_big_preamp(Scope.CHANNEL_A)
    scope.set_big_preamp(Scope.CHANNEL_B)
    scope.set_sample_rate_divisor(0x7)
    scope_read_thread = ScopeReadThread(scope, data_sender)

    def stop_server_and_exit(signum, frame):
        print '\rStopping server'
        scope_read_thread.stop()
        control_panel_thread.stop()
        scope_read_thread.join()
        control_panel_thread.join()
        reactor.stop()

    def status_message(msg):
        print msg

    signal.signal(signal.SIGINT, stop_server_and_exit)
    scope_read_thread.start()
    control_panel_thread.start()

    reactor.listenTCP(server_port, ScopeFactory(client_list))
    reactor.callWhenRunning(
            status_message, 'Server started on port %d' % server_port)
    reactor.run()


def usage():
    print 'usage: python tekscope.py SCOPE_PORT CONTROLS_PORT [SERVER_PORT]'


if __name__ == "__main__":
    main()
