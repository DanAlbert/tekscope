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
"""
import sys
import socket
import datetime
import timeit
import math
import time
import serial
import array
import string
import types


def get_local_ip_address(target):
    """Returns the IP address of the local machine.

    Method taken from
    http://www.linux-support.com/cms/get-local-ip-address-with-python/
    """
    ipaddr = ''
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target, 8000))
        ipaddr = s.getsockname()[0]
        s.close()
    except:
        pass

    return ipaddr


def init(ipaddr, port, serversocket=None):
    """
    Init: Creates server socket and binds to the host, creates log file
    Arguments: Port to bind to
    Returns: serversocket
    """
    if serversocket is None:
            serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
            serversocket = serversocket
    serversocket.bind((ipaddr, port))
    log("L", "Serversocket bound to: " + ipaddr + ":" + str(port))
    serversocket.listen(5)
    return serversocket


def receive_start(serversocket):
    """
    Defining receive_handler : Recieves connections and bytes and forks new
    threads depending on what is recieved

    Arguments: serversocket
    Returns:
    Notes: While loop that uses a server socket to receive connections and fork
    new threads depending on what is recieved
    """
    while 1:
        (clientsocket, address) = serversocket.accept()
        log("L", "Client connected at: " + str(clientsocket.getpeername()))
        ct = receive_handler(clientsocket)


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



def log(type, message):
    """
    Log: Writes log messages to a timestamped file
    Arguments: Error Type and Message
    Returns:
    """
    with open("Server_log.txt", "a") as log_file:
        log_file.write(str(datetime.datetime.now()) + " - " + type + ": " + message+ "\n")
    print str(datetime.datetime.now()) + " - " + type + ": " + message + "\n"

# Speedtest: Times how long it takes to receive 5Mb of data from a socket
# Arguments: clientsocket
# Returns:

def itoa(n, base = 10):
    if type (n) != types.IntType:
        raise TypeError, 'First arg should be an integer'
    if (type (base) != types.IntType) or (base <= 1):
        raise TypeError, 'Second arg should be an integer greater than 1'
    output = []
    pos_n = abs (n)
    while pos_n:
        lowest_digit = pos_n % base
        output.append (str (lowest_digit))
        pos_n = (pos_n - lowest_digit) / base
    output.reverse ()
    if n < 0:
        output.insert (0, '-')
    return string.join (output, '')


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
    
    print "Running"

    # New Log File
    with open("Server_log.txt", "a") as log_file:
        log_file.write("\n\n\n" + str(datetime.datetime.now()) + " Python server started\n")
    log("Debug", "Testing Logging")

    receive_start(serversocket)

