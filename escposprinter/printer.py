#!/usr/bin/python
'''
@author: Manuel F Martinez <manpaz@bashlinux.com>
@organization: Bashlinux
@copyright: Copyright (c) 2012 Bashlinux
@license: GPL
'''
import os
import subprocess
from queue import Queue
from sys import platform
from time import sleep

import usb.core
import usb.util
import serial
import socket


from escposprinter.escpos import Escpos, EscposIO


class Usb(Escpos):
    """ Define USB printer """

    def __init__(self, idVendor, idProduct, interface=0, in_ep=0x82, out_ep=0x01):
        """
        @param idVendor  : Vendor ID
        @param idProduct : Product ID
        @param interface : USB device interface
        @param in_ep     : Input end point
        @param out_ep    : Output end point
        """
        self.idVendor  = idVendor
        self.idProduct = idProduct
        self.interface = interface
        self.in_ep     = in_ep
        self.out_ep    = out_ep
        self.open()


    def open(self):
        """ Search device on USB tree and set is as escpos device """
        self.device = usb.core.find(idVendor=self.idVendor, idProduct=self.idProduct)
        if self.device is None:
            print ("Cable isn't plugged in")

        if self.device.is_kernel_driver_active(0):
            try:
                self.device.detach_kernel_driver(0)
            except usb.core.USBError as e:
                print ("Could not detatch kernel driver: %s" % str(e))

        try:
            self.device.set_configuration()
            self.device.reset()
        except usb.core.USBError as e:
            print ("Could not set configuration: %s" % str(e))


    def _raw(self, msg):
        """ Print any command sent in raw format """
        self.device.write(self.out_ep, msg, self.interface)


    def __del__(self):
        """ Release USB interface """
        if self.device:
            usb.util.dispose_resources(self.device)
        self.device = None



class Serial(Escpos):
    """ Define Serial printer """

    def __init__(self, devfile="/dev/ttyS0", baudrate=9600, bytesize=8, timeout=1):
        """
        @param devfile  : Device file under dev filesystem
        @param baudrate : Baud rate for serial transmission
        @param bytesize : Serial buffer size
        @param timeout  : Read/Write timeout
        """
        self.devfile  = devfile
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.timeout  = timeout
        self.open()


    def open(self):
        """ Setup serial port and set is as escpos device """
        self.device = serial.Serial(port=self.devfile, baudrate=self.baudrate, bytesize=self.bytesize, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=self.timeout, dsrdtr=True)

        if self.device is not None:
            print ("Serial printer enabled")
        else:
            print ("Unable to open serial printer on: %s" % self.devfile)


    def _raw(self, msg):
        """ Print any command sent in raw format """
        self.device.write(msg)


    def __del__(self):
        """ Close Serial interface """
        if self.device is not None:
            self.device.close()



class Network(Escpos):
    """ Define Network printer """

    printerQueue = Queue()


    def __init__(self,host,port=9100):
        """
        @param host : Printer's hostname or IP address
        @param port : Port to write to
        """
        self.host = host
        self.port = port
        self.open()

    #Static method to check if the printer is alive and reachable to the given hostname and port
    def isAlive(host, port):
        response = None
        if ('darwin' in platform or 'linux2' in platform or 'linux' in platform):
            response = str(subprocess.Popen("nc -z -w 1 {0} {1}  &> /dev/null && echo 'up' || echo 'down'".format(str(host), str(port)), stdout=subprocess.PIPE, shell=True).stdout.read(), 'utf-8').strip()
        elif ('windows' in platform or 'win32' in platform):  # For Windows-Based Systems
            #Windows natively doesn't implement netcat, due to that, we are using an external porting of netcat for windows
            netcatPath = os.path.join(os.path.abspath(__package__), 'nc.exe')
            response = str(subprocess.Popen("{0} -z -w 1 {1} {2}  > NUL && echo up || echo down".format(str(netcatPath),str(host), str(port)), stdout=subprocess.PIPE, shell=True).stdout.read(), 'utf-8').strip()
        else:
            raise OSError("Unable to determine System type")

        if (response is not None):
            if response == 'up':
                return True
            else:
                return False
        else:
            raise ValueError("Invalid response Value, it's none, something went really wrong")

    def open(self):
        """ Open TCP socket and set it as escpos device """
        self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.device.connect((self.host, self.port))

        if self.device is None:
            print ("Could not open socket for %s" % self.host)

    def _raw(self, msg):
        """ Print any command sent in raw format """
        if self.printerQueue is not None:
            if (type(msg) is bytes):
                self.printerQueue.put(msg)
            elif (type(msg) is str):
                self.printerQueue.put(bytes(msg, encoding='utf8'))



            while not self.printerQueue.empty():
                queueElementToPrint = self.printerQueue.get()
                if self.device is not None:
                    if (type(queueElementToPrint) is bytes):
                        self.device.send(queueElementToPrint)
                    elif (type(queueElementToPrint) is str):
                        self.device.send(bytes(queueElementToPrint, encoding='utf8'))
                    else:
                        print("Error Type while sending data to printer Raw Socket, unrecognized format!")


        else:
            raise Exception("Printer Queue is None, something went really wrong with the class istance")

    def do_stuff(self, q):
        pass

    def __del__(self):
        """ Close TCP connection """
        if (self.device is not None):
            self.device.close()






class File(Escpos):
    """ Define Generic file printer """

    def __init__(self, devfile="/dev/usb/lp0"):
        """
        @param devfile : Device file under dev filesystem
        """
        self.devfile = devfile
        self.open()


    def open(self):
        """ Open system file """
        self.device = open(self.devfile, "wb")

        if self.device is None:
            print ("Could not open the specified file %s" % self.devfile)


    def _raw(self, msg):
        """ Print any command sent in raw format """
        self.device.write(msg);


    def __del__(self):
        """ Close system file """
        self.device.close()
