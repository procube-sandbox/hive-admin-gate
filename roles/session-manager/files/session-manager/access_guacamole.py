import json
import os
import requests
import urllib
import uuid

GUACAMOLE_URL = os.environ.get("GUACAMOLE_URL")
GUACAMOLE_USERNAME = os.environ.get("GUACAMOLE_USERNAME")
GUACAMOLE_PASSWORD = os.environ.get("GUACAMOLE_PASSWORD")


def _api_request(
    method,
    path,
    data=None,
    token=None,
    headers={"Content-Type": "application/json"},
    toJSON=True,
):
    url = GUACAMOLE_URL + path

    if token:
        headers["Guacamole-Token"] = token

    response: requests.Response = method(url, data=data, headers=headers)

    if response.status_code >= 400:
        raise Exception(f"Guacamole API error: {response.text}")
    if toJSON:
        return response.json()
    else:
        return response


def generate_auth_token():
    path = "/api/tokens"
    params = {"username": GUACAMOLE_USERNAME, "password": GUACAMOLE_PASSWORD}
    params = urllib.parse.urlencode(params)
    return _api_request(
        requests.post,
        path,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def get_user(token: str):
    path = "/api/tokens"
    params = {"token": token}
    params = urllib.parse.urlencode(params)
    return _api_request(
        requests.post,
        path,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def create_connection(
    token: str,
    database: str,
    info: dict,
    params: dict,
    type: str,
    hostname: str,
    port: str,
    origin_identifier: str | None,
    username: str | None = None,
    password: str | None = None,
    swc_uid: str | None = None,
):
    path = f"/api/session/data/{database}/connections"
    data = info
    if "activeConnections" in data:
        del data["activeConnections"]
    if "lastActive" in data:
        del data["lastActive"]
    data.update(
        {
            "name": f"{info["name"].split(":")[0]}:{uuid.uuid4()}",
            "idmIdentifier": type,
        }
    )
    params.update(
        {
            "hostname": hostname,
            "port": port,
            "originIdentifier": origin_identifier,
            **({"swcUid": swc_uid} if swc_uid else {}),
            **({"username": username} if username else {}),
            **({"password": password} if password else {}),
        }
    )
    data["parameters"] = params

    return _api_request(requests.post, path, data=json.dumps(data), token=token)


def delete_connection(token: str, database: str, identifier: str) -> None:
    path = f"/api/session/data/{database}/connections/{identifier}"
    _api_request(requests.delete, path, token=token, toJSON=False)


def assign_user_to_connection(
    token: str, database: str, username: str, identifier: str
) -> None:
    path = f"/api/session/data/{database}/users/{username}/permissions"
    data_path = f"/connectionPermissions/{identifier}"
    data = [{"op": "add", "path": data_path, "value": "READ"}]
    _api_request(requests.patch, path, data=json.dumps(data), token=token, toJSON=False)


def get_connection_info(token: str, database: str, identifier: str):
    path = f"/api/session/data/{database}/connections/{identifier}"
    return _api_request(requests.get, path, token=token)


def get_connection_params(token: str, database: str, identifier: str):
    path = f"/api/session/data/{database}/connections/{identifier}/parameters"
    return _api_request(requests.get, path, token=token)


def get_all_connections(token: str, database: str):
    path = f"/api/session/data/{database}/connections"
    return _api_request(requests.get, path, token=token)


def get_work_from_identifier(token: str, database: str, idm_identifier: str):
    path = f"/api/session/data/{database}/works"
    response = _api_request(requests.get, path, token=token)
    for v in reversed(response.values()):
        if v["idmIdentifier"] == idm_identifier:
            return v
    raise Exception("Work not found")


def get_all_works(token: str, database: str):
    path = f"/api/session/data/{database}/works"
    return _api_request(requests.get, path, token=token)
