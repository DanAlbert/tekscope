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
    GET /scope -> server sends a response containing scope history
    PUT /scope -> update scope parameters

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
import sys
import datetime
import math
import time
import serial

from flask import Flask

app = Flask(__name__)

@app.route('/scope', methods=['GET'])
def get_scope():
    pass


@app.route('/scope', methods=['PUT'])
def put_scope():
    pass


def receive_handler(clientsocket):
    clientsocket.settimeout(500)
    log("L", "Client socket timeout set to " + str(clientsocket.gettimeout()))

#        channel1data = [0] * 1200        # Create empty array ready to receive result
#        channel2data = [0] * 1200        # Create empty array ready to receive result

    j=0
    channel1packet = "CHONE,1000,"
    channel2packet = "CHTWO,1000,"
    for i in range(0, 1027):
        channel1data[i] = 100*math.sin(((i) * .01))
        channel2data[i] = 50*math.sin(((i) *.05))
        channel1packet = channel1packet + "%03.0f" % channel1data[i] + ","
        channel2packet = channel2packet + "%03.0f" % channel2data[i] + ","
        # Receive start bytes
    channel1packet = channel1packet + "\n"
    channel2packet = channel2packet + "\n"
#        log("F", channel1packet)
    out = [0] * 6000
    while 1:
        try:
            while 1:
                time.sleep(.05)
                clientsocket.send(channel1packet)
                time.sleep(.05)
                clientsocket.send(channel2packet)
                ser.write("S C 2 0" + '\r\n')
                ser.write("S G" + '\r\n')
                out = ser.read(3)
                samples = ord(out[1]) * 256 + ord(out[2])
                #print "Returned ending address of " + str(samples)
                ser.write("S B" + '\r\n')
                out = ser.read(1)
                out = ser.read(4096)
                if out != '':
                    j = 4*(samples)+4
                    for i in range(0, 1023):
                        j = j % 4096
                        channel1data[(i)] = ord(out[j]) * 256 + ord(out[(j+1)% 4096])
                        channel2data[(i)] = ord(out[(j+2)% 4096]) * 256 + ord(out[(j+3)% 4096])
                        j = (j + 4)
                channel1packet = "CHONE,1024,7,"
                channel2packet = "CHTWO,1024,7,"
                for i in range(0, 1027):
                    channel1packet = channel1packet + "%03.0f" % ((511-channel1data[i])) + ","
                    channel2packet = channel2packet + "%03.0f" % ((511-channel2data[i])) + ","
                channel1packet = channel1packet + "\n"
                channel2packet = channel2packet + "\n"        
        except:
            log("E", "Could not send data!")
            break
    try:
        clientsocket.close();
    except:
        log("E", "Client Closed Socket?")
                

def receive_data(clientsocket, buffer):
    """
    Receive_data: Receives a specified amount of data
    Arguments: clientsocket, buffersize
    Returns: 
    """
    msg = ''
    while len(msg) < buffer:
        data = clientsocket.recv(buffer - len(msg))
        if data == '':
            raise RuntimeError("No data received, or socket connection broken")
        msg = msg + data


# Speedtest: Times how long it takes to receive 5Mb of data from a socket
# Arguments: clientsocket
# Returns:

if __name__ == "__main__":
    # Initiate on port 15151
    serversocket = init(get_local_ip_address("google.com"), 15151)
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
    

    out = [0] * 6000
    
    receive_start(serversocket)

