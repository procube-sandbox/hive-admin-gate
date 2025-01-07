#!/usr/bin/env python3
import json
import sys
import subprocess
import time

MAX_RETRY_COUNT = 60
RETRY_INTERVAL = 5

CONSUL_CONFIG_PATH='/etc/consul.json'

def load_json(path):
    with open(path, 'r') as fd:
        try:
            return json.load(fd)
        except json.JSONDecodeError as e:
            raise  Exception(f'fail to parse json {path}: {e}')

def check_peers(num_peers):
    try:
        result = subprocess.run(['consul', 'operator', 'raft', 'list-peers'], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
        line_count = len(result.stdout.splitlines()) - 1
        if line_count != num_peers:
            print(f'output liene count {line_count} does not match bootstrap_expected {num_peers}', file=sys.stderr, flush=True)
            return False
    except subprocess.CalledProcessError as e:
        print(f'failed to exec "consul operator raft list-peers": {e.output}', file=sys.stderr, flush=True)
        return False
    return True

def main():
    consul_config = load_json(CONSUL_CONFIG_PATH)
    num_peers = consul_config['bootstrap_expect']

    if (not num_peers) or num_peers == 1:
        print('No bootstrap expected', flush=True)
        sys.exit(0)
    print(f'Wait for {num_peers} consul peer nodes', flush=True)
    count = 0
    while True:
        if check_peers(num_peers):
            break
        count += 1
        print(f'fail to check peers, so retry after {RETRY_INTERVAL} seconds, this is the {count} time of a maximum of {MAX_RETRY_COUNT} retries.', flush=True)
        if count > MAX_RETRY_COUNT:
            raise Exception(f'Retry count exceeded max retry count {MAX_RETRY_COUNT}, ')
        time.sleep(RETRY_INTERVAL)
    print('Consul peer node connectivity confirmed', flush=True)
    sys.exit(0)

main()
