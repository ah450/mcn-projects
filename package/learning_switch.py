from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_bool
import time

log = core.getLogger()

class LearningSwitch(object):
  """
  The learning switch "brain" associated with a single OpenFlow switch.
  When we see a packet, we'd like to output it on a port which will
  eventually lead to the destination.  To accomplish this, we build a
  table that maps addresses to ports.
  We populate the table by observing traffic.  When we see a packet
  from some source coming from some port, we know that source is out
  that port.
  When we want to forward traffic, we look up the desintation in our
  table.  If we don't know the port, we simply send the message out
  all ports except the one it came in on.  (In the presence of loops,
  this is bad!).
  In short, our algorithm looks like this:
  For each packet from the switch:
  1) Use source address and switch port to update address/port table
  2) Is transparent = False and either Ethertype is LLDP or the packet's
     destination address is a Bridge Filtered address?
     Yes:
        2a) Drop packet -- don't forward link-local traffic (LLDP, 802.1x)
            DONE
  3) Is destination multicast?
     Yes:
        3a) Flood the packet
            DONE
  4) Port for destination address in our address/port table?
     No:
        4a) Flood the packet
            DONE
  5) Is output port the same as input port?
     Yes:
        5a) Drop packet and similar ones for a while
  6) Install flow table entry in the switch so that this
     flow goes out the appopriate port
     6a) Send the packet out appropriate port
  """
  def __init__(self, connection, transparent):
    super(LearningSwitch, self).__init__()
    self.connection = connection
    self.transparent = transparent

    self.macToPortTranslationTable = {}
    connection.addListeners(self)

  def _handle_PacketIn(self, event):
    packet = event.parsed

    def flood(message=None):
      """Floods the packet"""
      msg = of.ofp_packet_out()
      if message is not None:
        log.debug(message)
      msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      msg.data = event.ofp
      msg.in_port = event.port
      self.connection.send(msg)

    def drop (duration = None):
      """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id is not None:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)

    self.macToPort[packet.src] = event.port

    if not self.transparent:
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
        drop()
    elif packet.dst.is_multicast:
      flood()
    else:
      if packet.dst not in self.macToPort:
        flood("Port for %s unknown -- flooding" % (packet.dst,))
      else:
        port = self.macToPort[packet.dst]
        if port == event.port:
          log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
            % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
          drop(10)
        else:
          log.debug("installing flow for %s.%i -> %s.%i" %
                           (packet.src, event.port, packet.dst, port))
          msg = of.ofp_flow_mod()
          msg.match = of.ofp_match.from_packet(packet, event.port)
          msg.idle_timeout = 10
          msg.hard_timeout = 30
          msg.actions.append(of.ofp_action_output(port = port))
          msg.data = event.ofp
          self.connection.send(msg)




class l2_learning (object):
  """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """
  def __init__ (self, transparent):
    core.openflow.addListeners(self)
    self.transparent = transparent

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    LearningSwitch(event.connection, self.transparent)


def launch (transparent=False):
  """
  Starts an L2 learning switch.
  """
  core.registerNew(l2_learning, str_to_bool(transparent))