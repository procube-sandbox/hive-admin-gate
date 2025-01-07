#!/usr/bin/env python3
import json
import sys
import subprocess
import socket
import re
import time
import os

MAX_RETRY_COUNT = 20
RETRY_INTERVAL = 5

RAFT_PORT=8300
GOSSIP_PORT=8301
CONSUL_CONFIG_PATH='/etc/consul.json'

def load_json(path):
    with open(path, 'r') as fd:
        try:
            return json.load(fd)
        except json.JSONDecodeError as e:
            raise  Exception(f'fail to parse json {path}: {e}')

def write_json(path, content):
    with open(path, 'w') as fd:
        json.dump(content, fd, indent=4)

address_re = re.compile(r'Address: (.*)')

def get_peers(service_name):
    try:
        result = subprocess.run(['nslookup',service_name], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
        answer = False
        for line in result.stdout.splitlines():
            if answer:
                address_match = address_re.match(line)
                if address_match:
                    yield address_match.groups()[0]
            elif line == 'Non-authoritative answer:':
                answer = True
    except subprocess.CalledProcessError as e:
        print(f'failed to exec "nslookup {service_name}": {e.output}', file=sys.stderr, flush=True)
        yield []

# This function only supports raft protocol 2
def setup_raft_peers(peers):
    os.makedirs('/var/consul/raft/', exist_ok=True)
    write_json('/var/consul/raft/peers.json', list(map(lambda x: f'{x}:{RAFT_PORT}', peers)))

def setup_consul_json(consul_config, peers):
    consul_config['retry_join'] = list(map(lambda x: f'{x}:{GOSSIP_PORT}', peers))
    write_json(CONSUL_CONFIG_PATH, consul_config)


def main():
    print('Start setting up consul peer nodes', flush=True)
    consul_config = load_json(CONSUL_CONFIG_PATH)
    num_peers = consul_config['bootstrap_expect']

    if (not num_peers) or num_peers == 1:
        print('No bootstrap expected', flush=True)
        sys.exit(0)
    service_name = socket.gethostname()
    count = 0
    while True:
        peers = list(get_peers(service_name))
        if len(peers) >= num_peers:
            break
        count += 1
        print(f'nslookup {service_name} returns peers: {peers}, it is not enough for bootstrap_expect: {num_peers} in {CONSUL_CONFIG_PATH}, so retry after {RETRY_INTERVAL} seconds, this is the {count} time of a maximum of {MAX_RETRY_COUNT} retries.', flush=True)
        if count > MAX_RETRY_COUNT:
            raise Exception(f'Retry count exceeded max retry count {MAX_RETRY_COUNT}, nslookup return addresses {peers}')
        time.sleep(RETRY_INTERVAL)

    #  write_json('/var/consul/raft/peers.json', list(map(lambda x: f'{x}:{RAFT_PORT}', peers)))
    # In order to generate peers.json corresponding to raft protocol 3,
    # each IP address must be mapped to nodeid, but it is not possible.
    # setup_raft_peers(peers)
    setup_consul_json(consul_config, peers)
    print('Complete setting up consul peer nodes', flush=True)
    sys.exit(0)

main()
