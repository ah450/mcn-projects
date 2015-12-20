from mininet.net import Mininet
from mininet.topolib import TreeTopo
from mininet import RemoteController
from mininet.cli import CLI

tree4 = TreeTopo(depth=2,fanout=2)
net = Mininet(topo=tree4, controller=None)
net.addController('firewall', controller=RemoteController, ip="127.0.0.1",
    port=6633)
net.start()
CLI(net)
net.stop()