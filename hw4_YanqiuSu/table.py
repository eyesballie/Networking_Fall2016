# This example is using Python 2.7
import os
import threading


# Class that abstract routing table. This class is thread safe.
class ForwardingTable:
  # Constructor. '_table' is dictionary keyed on router ID, and values
  # are (next_hop,cost) pairs.
  def __init__(self):
    self._table = {}
    self._lock = threading.Lock()


  # Return current forwarding table as a list of tuples
  # (id,next_hop,cost).
  def snapshot(self):
    entries = []
    with self._lock:
      for router_id in self._table:
        next_hop, cost = self._table[router_id]
        entries.append((router_id, next_hop, cost))
    return entries


  # Reset routing table by snapshot, where snapshot is a list of
  # tuples (id,next_hop,cost).
  def reset(self, snapshot):
    with self._lock:
      self._table = {}
      for (dest, next_hop, cost) in snapshot:
        self._table[dest] = (next_hop, cost)


  # Return current number of entries in forwarding table.
  def size(self):
    return len(self._table)


  def __str__(self):
    entries = ['ID\tNextHop\tCost' + os.linesep]
    with self._lock:
      for router_id in self._table:
        next_hop, cost = self._table[router_id]
        entries.append(''.join([str(router_id), '\t',
                                str(next_hop), '\t',
                                str(cost), os.linesep]))
    return ''.join(entries)

  def find_cost(self, new_id, new_next_hop):
    for (id,next_hop,cost) in self.snapshot():
      if id == new_id and next_hop == new_next_hop:
        return cost
    return -1

  def find_cost_to_dest(self, dest_id):
    for (id,next_hop,cost) in self.snapshot():
      if id == dest_id:
        return cost
    return -1

  def add_entry(self, tuple):
    print 'add_entry', tuple
    snapshot = self.snapshot()
    print 'add_entry: before appending, snapshot is', snapshot
    snapshot.append(tuple)
    print 'add_entry: after appending, snapshot is', snapshot
    self.reset(snapshot)

  def replace_entry(self, tuple):
    print 'replace_entry', tuple
    snapshot = self.snapshot()
    print 'replace_entry: before replace, snapshot is', self.snapshot()
    for i in range(len(snapshot)):
      if snapshot[i][0] == tuple[0]:
        snapshot = snapshot[:i] + [tuple] + snapshot[i+1:]
        break
    self.reset(snapshot)
    print 'add_entry: after appending, snapshot is', self.snapshot()