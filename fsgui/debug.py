sock = list(results.keys())[0]

node_id, sub = self.sock_dict[sock]

data = sub.recv()
print(data)