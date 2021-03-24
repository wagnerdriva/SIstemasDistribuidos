# saved as greeting-client.py
import Pyro5.api

name = input("What is your name? ").strip()

greeting_maker = Pyro5.api.Proxy("PYRONAME:PeerA")     # get a Pyro proxy to the greeting object
print(greeting_maker.get_fortune(name))   # call method normally