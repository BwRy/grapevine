#/usr/bin/python

import socket
import select
from threading import Thread
import time
import signal
import sys

class Host:
    """Host does monitoring of the host and allows control through callbacks."""
    # Instance Variables
    ip = "127.0.0.1"
    port = 10001
    state =  0 # Uninitialised
    sock = None
    callback_set = {}
    mon_timeout = 0.02
    mon_ticks = 0

    # Constants
    UNINITIALISED = 0
    CONNECTED = 1
    TERMINATED = -1
    UNCONNECTED = -2

    def __init__(self, ip, port, callback_set = {}):
        self.ip = ip
        self.port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        if callback_set == {}:
            self.callback_set['unable_to_connect'] = self.__default_unable_to_connect_callback
            self.callback_set['crash_detected'] =  self.__default_crash_detected_callback
            self.callback_set['data_received'] =  self.__default_data_received_callback

            
    # Internal host functions

    def __send_cmd(self, data):
        self.sock.sendto(data, (self.ip, self.port))

    def __call_callback(self, event):
        self.callback_set[event]()

    @staticmethod
    def __default_crash_detected_callback():
        print "Advice: Crash detected event is not handled."

    @staticmethod
    def __default_unable_to_connect_callback():
        print "Advice: Unable to connect event is not handled."

    @staticmethod
    def __default_data_received_callback(data):
        print "\nData is Received:\n", data

    def start(self):
        Thread(target=self.monitor, name="monitor").start()
        self.__send_cmd("hello")

    def monitor(self):
        """Run in a separate thread to block on select calls. On the first run the timeout is set to 5 seconds, otherwise it takes a minute to timeout. Pings should be sent every 2 seconds so if there is no response in a minute, it is assumed that a crash has occured and the crash_detected callback will be called. On the first run, it will call the unable_to_connect callback."""
        while self.state >= 0:
            self.mon_ticks = self.mon_ticks + 1
            ready = select.select([self.sock], [], [], self.mon_timeout)
            if ready[0]:
                data = self.sock.recv(4092)
                self.__handle(data)
                ready = None
            self.__tick_check()

    def __tick_check(self):
        ticks_per_sec = 1/self.mon_timeout
        secs_elapsed = self.mon_ticks/ticks_per_sec
        if secs_elapsed > 5.0 and self.state == self.UNINITIALISED:
            self.__call_callback("unable_to_connect")
            self.state = self.UNCONNECTED
        

    def __handle(self, data):
        self.callback_set['data_received'](data)
        if data.startswith("hello from "):
            self.state = self.CONNECTED

    def stop(self):
        self.state = self.TERMINATED

    def set_state(self, state):
        self.state = state
        
    def is_host(self, ip, port):
        if self.ip == ip and self.port == int(port):
            return True
        else:
            return False

    # Command sending functions

    def shutdown(self):
        self.__send_cmd("exit")

    def bye(self):
        self.__send_cmd("bye")

    def fuzz(self):
        self.__send_cmd("fuzz")

    def stopfuzz(self):
        self.__send_cmd("stopfuzz")

    def loadgen(self):
        self.__send_cmd("loadgen")

class HostsController:
    hosts = [] # A list of Hosts
    log_ip = "127.0.0.1" # Externally accessible host IP address.
    log_port = 5000
    sock = None
    current_host = None
    
    def __init__(self, hosts = [], log_ip = "127.0.0.1", log_port = 5000):
        # hosts is to be a list of tuples in the form (addr, port)
        for i in hosts:
            ip, port = i
            self.add_new_host(ip, port)
        self.log_ip = log_ip
        self.log_port = log_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def __send_cmd(self, cmd):
        self.sock.sendto(cmd, (self.current_host.ip, 
                                  self.current_host.port))        

    def connect(self, ip, port):
        new_host = True
        for i in self.hosts:
            if i.is_host(ip, port):
                new_host = False
        if new_host:
            self.add_new_host(ip, port)
        self.set_current_host(ip, port)

    def add_new_host(self, ip, port):
        for i in self.hosts:
            if i.is_host(ip, port):
                return False
        new_host = Host(ip, port)
        self.hosts.append(new_host)
        new_host.start()

    def remove_host(self, ip, port):
        for i in self.hosts:
            if i.is_host(ip, port):
                i.stop()
                self.hosts.remove(i)
        
    def set_current_host(self, ip, port):
        for i in self.hosts:
            if i.is_host(ip, port):
                self.current_host = i

    def set_log(self, ip, port):
        self.log_ip = ip
        self.log_port = int(port)
        # Inform all hosts.

    def __interrupt_handler(self, sig_no, stack_frame):
        self.__safe_exit("Interrupt signal detected, terminating program.")

    # Ensuring a thread safe exit.
    def safe_exit(self, reason):
        print reason
        for i in self.hosts:
            i.bye()
            i.state = Host.TERMINATED
        time.sleep(0)
        sys.exit()