import zmq
import json
import uuid

import signal

# [SC] to capture the keyboard interrput command (Ctrl + C)
signal.signal(signal.SIGINT, signal.SIG_DFL)


# [SC] make sure client has a unique id otherwise client request may be ignored
identity = f"client-{uuid.uuid1()}"
ipa = "localhost"
port = "5570"

# [SC] opening a connection to the service
print("Starting the client")
context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.setsockopt_string(zmq.IDENTITY, identity)
socket.connect(f"tcp://{ipa}:{port}")

print("Setting the client poller")
poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)

# [SC] send a request
print("Sending a request to the remove service")
#socket.send_string("What is the average temperature for each neighborhood in Amsterdam")
socket.send_string("What is the population of Utrecht")

# [SC] wait for a reply
print("Waiting for a reply ...")
while True:
    # [SC] wait for 30 seconds for a message to arrive, otherwise terminate
    sockets = dict(poller.poll(30000))
    if sockets:
        if sockets.get(socket) == zmq.POLLIN:
            msg = socket.recv_string()
            print(f"Client received a reply: {msg}")
            break
    else:
        # [SC][TODO] code if no reply is received
        break

socket.close()
context.term()