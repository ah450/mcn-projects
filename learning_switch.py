from mininet.net import mininet
from mininet.node import OVSSwitch, Controller, RemoteController
from mininet.topolib import TreeTopo
from mininet.cli import CLI

c0 = Controller('c0', port=6633)


topo = TreeTopo( depth=2, fanout=2 )
net = Mininet( topo=topo, build=True )
net.start()
CLI(net)
net.stop()