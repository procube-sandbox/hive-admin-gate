import json
import os
import requests

SW_LISTENER_REST = os.environ.get("SW_LISTENER_REST")


def open_port(uid: str, port: int, connect_address: str, connect_port: int):
    url = SW_LISTENER_REST + "/open"
    headers = {"Content-Type": "application/json"}
    params = json.dumps(
        {
            "uid": uid,
            "port": port,
            "connect_address": connect_address,
            "connect_port": connect_port,
        }
    )
    return requests.post(url, data=params, headers=headers)


def close_port(port: int):
    url = SW_LISTENER_REST + "/close"
    headers = {"Content-Type": "application/json"}
    params = json.dumps(
        {
            "port": port,
        }
    )
    return requests.delete(url, data=params, headers=headers)
