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
    signally that the sample is complete, and HI and LO forming a 10-bit address
    of the sample in the scope's buffer.

    The buffer can be accessed with "S B\r\n"
    The scope will respond with the entire scope memory (4KB) and one additional
    byte (packet is preceded by 'D'). The buffer format returned is A1a1B1b1C1c1
    where A1 and a1 make the first 10-bit sample value, B1 and b1 make the
    second 10-bit sample value, and so on.

    Application organization:

    Communication with the scope should be done in a separate process, as either
    application crashing should not kill the other. The scope process can
    communicate with the service with a socket, a pipe or shared memory.

    Communication with the controls should follow a similar paradigm. A separate
    process can post to the web service whenever control information needs to be
    updated.
"""
import signal
from twisted.internet import reactor, protocol

import scope


class ScopeProtocol(protocol.Protocol):
    def __init__(self, client_list):
        self.client_list = client_list

    def connectionMade(self):
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


class ScopeDataSender():
    def __init__(self, client_list):
        self.client_list = client_list

    def append(self, data):
        for client in self.client_list:
            client.transport.write(str(data))


def main():
    port = 5000
    client_list = set()

    data_sender = ScopeDataSender(client_list)
    scope_thread = scope.ScopeThread(data_sender)

    def stop_server_and_exit(signum, frame):
        print '\rStopping server'
        scope_thread.stop()
        scope_thread.join()
        reactor.stop()

    def status_message(msg):
        print msg

    signal.signal(signal.SIGINT, stop_server_and_exit)
    scope_thread.start()

    reactor.listenTCP(port, ScopeFactory(client_list))
    reactor.callWhenRunning(status_message, 'Server started on port %d' % port)
    reactor.run()


if __name__ == "__main__":
    main()
