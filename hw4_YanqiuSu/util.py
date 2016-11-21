# This example is using Python 2.7
import threading


# Convenient class to run a function periodically in a separate
# thread.
class PeriodicClosure:
  def __init__(self, handler, interval_sec):
    self._handler = handler
    self._interval_sec = interval_sec
    self._timer = None

  def _timeout_handler(self):
    self._handler()
    self.start()

  def start(self):
    self._timer = threading.Timer(self._interval_sec, self._timeout_handler)
    self._timer.start()

  def stop(self):
    if self._timer:
      self._timer.cancel()


def dest_id_in_snapshot(dest_id, snapshot):
  for tuple in snapshot:
    if dest_id == tuple[0]:
      return True
  return False

def find_cost_to_dest(dest_id, snapshot):
  for tuple in snapshot:
    if dest_id == tuple[0]:
      return tuple[2]
  return -1

def replace_tuple(new_tuple, snapshot):
  for i in range(len(snapshot)):
    if snapshot[i][0] == new_tuple[0]:
      new_snapshot = snapshot[:i] + [tuple] + snapshot[i + 1:]
      return new_snapshot
  return snapshot


