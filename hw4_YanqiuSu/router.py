# This example is using Python 2.7
import os.path
import socket
import table
import threading
import util
import struct

_CONFIG_UPDATE_INTERVAL_SEC = 5

_MAX_UPDATE_MSG_SIZE = 1024
_BASE_ID = 8000

def _ToPort(router_id):
  return _BASE_ID + router_id

def _ToRouterId(port):
  return port - _BASE_ID


class Router:
  def __init__(self, config_filename):
    # ForwardingTable has 3 columns (DestinationId,NextHop,Cost). It's
    # threadsafe.
    self._forwarding_table = table.ForwardingTable()
    # Config file has router_id, neighbors, and link cost to reach
    # them.
    self._config_filename = config_filename
    self._router_id = None
    # Socket used to send/recv update messages (using UDP).
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.neighbors = []
    #threading.Thread(target=self.packet_reader).start()

  def start(self):
    # Start a periodic closure to update config.
    self._config_updater = util.PeriodicClosure(
        self.load_config, _CONFIG_UPDATE_INTERVAL_SEC)
    self._config_updater.start()
    # TODO: init and start other threads.
    while True:
      self.packet_reader()

  def stop(self):
    if self._config_updater:
      self._config_updater.stop()
    # TODO: clean up other threads.


  def load_config(self):
    assert os.path.isfile(self._config_filename)
    with open(self._config_filename, 'r') as f:
      router_id = int(f.readline().strip())
      # Only set router_id when first initialize.
      first_initialize = False
      if not self._router_id:
        first_initialize = True
        self._socket.bind(('localhost', _ToPort(router_id)))
        self._router_id = router_id
      # TODO: read and update neighbor link cost info.
      list = []
      reset_forwarding_table = False
      while self.peek_line(f):
        neighbor, cost = f.readline().split(',')
        if first_initialize:
          self.neighbors.append(int(neighbor))
        prev_cost = self._forwarding_table.find_cost_to_dest(int(neighbor))
        print 'prev_cost is', prev_cost
        print 'new_cost is', cost
        if prev_cost == -1 or prev_cost > cost:
          print 'prev_cost is larger than new_cost'
          list.append((int(neighbor), int(neighbor), int(cost)))
          reset_forwarding_table = True
      if reset_forwarding_table:
        self._forwarding_table.reset(list)
    self.make_and_send_msg()


  def peek_line(self, f):
    pos = f.tell()
    line = f.readline()
    f.seek(pos)
    return line

  def make_and_send_msg(self):
    entry_count = self._forwarding_table.size()
    packet = struct.pack('!H', entry_count)
    for id,next_hop,cost in self._forwarding_table.snapshot():
      packet += struct.pack('!HH', id, cost)
    #send table to neighbors
    for neighbor_id in self.neighbors:
      self._socket.sendto(packet, ('localhost', _ToPort(neighbor_id)))
      print 'I sent %s to %s' % (self._forwarding_table.__str__(), _ToPort(neighbor_id))

  def packet_reader(self):
    msg, addr = self._socket.recvfrom(_MAX_UPDATE_MSG_SIZE)
    #print 'msg is %s and addr is %s' % (msg, addr)
    router_id = _ToRouterId(addr[1])
    print 'packet_reader: I received %s from %s' % (repr(msg), router_id)
    self.update_forwarding_table(msg, router_id)
    print 'packet_reader: I updated forwarding table\n', self._forwarding_table.__str__()

  def update_forwarding_table(self, msg, router_id):
    entry_count = (struct.unpack('!H', msg[:2]))[0]
    k = 2
    for i in range(entry_count):
      print 'i is', i
      dest_id = (struct.unpack('!H', msg[k:k+2]))[0]
      cost = (struct.unpack('!H', msg[k+2:k+4]))[0]
      k += 4
      if dest_id == self._router_id:
        continue
      if dest_id not in self._forwarding_table._table:
        print 'this is a new destination, ', dest_id
        cost_to_neighbor = self._forwarding_table.find_cost(dest_id, router_id)
        tuple = (dest_id, router_id, cost + cost_to_neighbor)
        self._forwarding_table.add_entry(tuple)
        self.make_and_send_msg()
      else:
        print 'recv: this is an old destination, ', dest_id
        cost_to_neighbor = self._forwarding_table.find_cost_to_dest(router_id)
        if self._forwarding_table.find_cost_to_dest(dest_id) > cost_to_neighbor + cost:
          print 'recv: found less cost for %s, old cost %s, new cost %s ' % (dest_id, self._forwarding_table.find_cost_to_dest(dest_id), cost_to_neighbor + cost)
          tuple = (dest_id, router_id, cost + cost_to_neighbor)
          self._forwarding_table.replace_entry(tuple)
          self.make_and_send_msg()


