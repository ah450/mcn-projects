from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo
from mininet.node import RemoteController
from mininet.cli import CLI

tree4 = SingleSwitchTopo(12)
net = Mininet(topo=tree4, controller=None)
net.addController('poxController', controller=RemoteController, ip="127.0.0.1",
    port=6633)
net.start()
CLI(net)
net.stop()