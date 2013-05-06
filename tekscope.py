"""Backend service for the TekBots USB oscilloscope.

Authors:
    Dan Albert <dan@gingerhq.net>
    Aidan Daly-Jensen

Developer documentation:
    Encoder controls send 1R for 1 tick right and 1L for one tick left.
    Button status is indicated by AD (for button A down)
    To turn on light A, send AO

    The service needs to allow the scope front end to reconnect at any time
    (since we are implementing this as a web service, that should be automatic).

    The controller (I assume Don is referring to the controller attached to the
    control console and not the scope) turns off occasionally, so don't expect
    to always see data on that channel.

    URL design information:
    PUT /scope -> update scope parameters
    PUT /controls -> update control panel information

    For the actual scope data, we may need to use something like this:
    http://www.w3.org/TR/streams-api/
    http://www.w3.org/TR/mediacapture-streams/

    Some docs on implementing streaming in the back end:
    http://flask.pocoo.org/docs/patterns/streaming/

    This might be useful for the front end:
    https://github.com/flowersinthesand/portal

    If we can't stream it, we may have to just open a socket and ditch the web
    service model.

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
    Communication with the tablet display should be done through a web service.
    This will be easiest to implement on the tablet, and easiest to port to a
    web application if need be.

    Communication with the scope should be done in a separate process, as either
    application crashing should not kill the other. To start, the scope
    communication process can simply POST (or PUT, whatever) data to the web
    service. Depending on performance, we may need to switch to something like
    shared memory instead.

    Communication with the controls should follow a similar paradigm. A separate
    process can post to the web service whenever control information needs to be
    updated.
"""
import json
import signal
import sys
import time

from flask import Flask, Response
app = Flask(__name__)

from scope import Scope

SCOPE = Scope()
STOPPING = False


def next_scope_data():
    global SCOPE
    return SCOPE.get_data()


@app.route('/scope', methods=['GET'])
def get_scope():
    def stream_scope_data():
        global STOPPING
        while not STOPPING:
            data = next_scope_data()
            if data:
                yield json.dumps(data)
    return Response(stream_scope_data())


@app.route('/scope', methods=['PUT'])
def put_scope():
    pass


if __name__ == '__main__':
    def sigint_handler(signum, frame):
        """Closes threads and kills streams on SIGINT.

        TODO: For some reason SIGINT needs to be raised twice. Once for the
              active stream, once for the application.
        """
        global SCOPE
        global STOPPING
        print '\rCaught SIGINT, quitting'
        SCOPE.read_thread.stop()
        STOPPING = True
        time.sleep(1)
        sys.exit(signum)

    SCOPE.read_thread.start()
    signal.signal(signal.SIGINT, sigint_handler)
    app.run(host='0.0.0.0')
