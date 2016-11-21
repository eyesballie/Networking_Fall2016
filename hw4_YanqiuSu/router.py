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
    # Stores distance from current router to neighbor, c(x, y)
    # It will only contain neighbors, which is different from forwarding table.
    self.neighbors_distance = {}
    # Stores the latest update message received from neighbors
    self.latest_update_message = {}
    # A list of tuples(dest_id,next_hop,cost), similar to the snapshot of
    # forwarding table. However,
    self.D = []

    # Config file has router_id, neighbors, and link cost to reach
    # them.
    self._config_filename = config_filename
    self._router_id = None
    # Socket used to send/recv update messages (using UDP).
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


  def start(self):
    # Start a periodic closure to update config.
    self._config_updater = util.PeriodicClosure(
        self.load_config, _CONFIG_UPDATE_INTERVAL_SEC)
    self._config_updater.start()
    # TODO: init and start other threads.
    while True:
      self.update_msg_reader()

  def stop(self):
    if self._config_updater:
      self._config_updater.stop()
    # TODO: clean up other threads.


  def load_config(self):
    assert os.path.isfile(self._config_filename)
    with open(self._config_filename, 'r') as f:
      router_id = int(f.readline().strip())
      first_initialize = False
      list = [(router_id, router_id, 0)]
      # When first initialize, set router_id
      if not self._router_id:
        first_initialize = True
        self._socket.bind(('localhost', _ToPort(router_id)))
        self._router_id = router_id
      # TODO: read and update neighbor link cost info.
      while self.peek_line(f):
        neighbor, cost = f.readline().split(',')
        self.neighbors_distance[int(neighbor)] = int(cost)
        # initialize forwarding table.
        if first_initialize:
          list.append((int(neighbor), int(neighbor), int(cost)))
      if first_initialize:
        self._forwarding_table.reset(list)
      #print 'load_config: setting self.D to ', list
      self.D = list
    self.make_and_send_msg()
      # We don't make changes to forwarding table, since when link
      # cost changes, we don't know what's going to be the shortest path.
      # We rely on neighbor's update message to calculate this.


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
    for neighbor_id in self.neighbors_distance:
      self._socket.sendto(packet, ('localhost', _ToPort(neighbor_id)))
      print 'Sent \n%s to %s\n' % (self._forwarding_table.__str__(), _ToPort(neighbor_id))

  def update_msg_reader(self):
    msg, addr = self._socket.recvfrom(_MAX_UPDATE_MSG_SIZE)
    #print 'msg is %s and addr is %s' % (msg, addr)
    router_id = _ToRouterId(addr[1])
    # for now, don't compare the latest message, just put in it.
    self.latest_update_message[router_id] = self.unpack_msg(msg)
    print 'update_msg_reader: Received msg from %s' % (router_id)
    self.recompute_dv()

  def recompute_dv(self):
    reset_forwarding_table = False
    for next_hop_id, dest_cost_list in self.latest_update_message.iteritems():
      #print 'next_hop_id is %s, dest_cost_list us %s' % (next_hop_id, dest_cost_list)
      for dest_cost_tuple in dest_cost_list:
        #print 'current dest_cost_tuple is ', dest_cost_tuple
        dest_id = dest_cost_tuple[0]
        cost_from_next_hop = dest_cost_tuple[1]
        new_cost = self.neighbors_distance[next_hop_id] + cost_from_next_hop
        new_tuple = (dest_id, next_hop_id, new_cost)
        dest_id_in_dv = False
        for i in range(len(self.D)):
          #print 'recompute_dv: start to iterate self.D ', self.D
          if self.D[i][0] == dest_id:
            #print 'recompute_dv: found a matching dest_id ', dest_id
            dest_id_in_dv = True
            old_cost = self.D[i][2]
            if new_cost < old_cost:
              #print 'recompute_dv: old_cost is %s and new_cost is %s' % (old_cost, new_cost)
              reset_forwarding_table = True
              self.D = self.D[:i] + [new_tuple] + self.D[i + 1:]
        if not dest_id_in_dv:
          #print 'dest_id is not in self.D, appending ', new_tuple
          reset_forwarding_table = True
          self.D.append(new_tuple)
    if reset_forwarding_table == True:
      #print 'reset_forwarding_table and send fowarding table '
      self._forwarding_table.reset(self.D)
      self.make_and_send_msg()


  def unpack_msg(self, msg):
    # result is a list of tuple, (dest_router_id, cost)
    result = []
    entry_count = (struct.unpack('!H', msg[:2]))[0]
    k = 2
    for i in range(entry_count):
      #print 'i is', i
      dest_id = (struct.unpack('!H', msg[k:k + 2]))[0]
      cost = (struct.unpack('!H', msg[k + 2:k + 4]))[0]
      result.append((dest_id, cost))
      k += 4
    return result