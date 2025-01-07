import os
import random
import requests
import logging
import sys
import memcache
import json
from flask import Flask, request, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
from access_guacamole import (
    generate_auth_token,
    get_user,
    create_connection,
    assign_user_to_connection,
    get_connection_info,
    get_connection_params,
    get_work_from_identifier,
)
from access_docker import create_service
from access_swl import open_port, close_port
from check_connection import check_connection

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Validate and fetch environment variables with default values
GUAC_DATABASE = os.environ.get("GUAC_DATABASE", "postgresql")
MEMCACHED_URL = os.environ.get("MEMCACHED_URL", "127.0.0.1:11211")
SW_LISTENER = os.environ.get("SW_LISTENER", "sw-listener")
UNAVAILABLE_PORTS = os.environ.get("UNAVAILABLE_PORTS", "")

mc = memcache.Client([MEMCACHED_URL])


def check_worker_permissions(username, work):
    if not (work.get("isWorker") or username == "guacadmin"):
        raise PermissionError("The specified user is not registered as a worker.")


def check_working_hours(username, work):
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    current_date = now.date()
    current_time = now.time()

    for period in work.get("periods", []):
        valid_from_date = datetime.strptime(period["validFrom"], "%Y-%m-%d").date()
        valid_until_date = datetime.strptime(period["validUntil"], "%Y-%m-%d").date()
        start_time = datetime.strptime(period["startTime"], "%H:%M:%S").time()
        end_time = datetime.strptime(period["endTime"], "%H:%M:%S").time()

        if (
            valid_from_date <= current_date <= valid_until_date
            and start_time <= current_time <= end_time
        ):
            return

    if username != "guacadmin":
        raise PermissionError("Worker cannot connect outside of working hours.")


def get_available_port(ports, unavailable_ports):
    all_ports = set(range(1025, 65536))
    unavailable_ports = set(map(int, unavailable_ports))
    available_ports = list(all_ports - ports - unavailable_ports)
    if not available_ports:
        raise RuntimeError("No available ports")
    return random.choice(available_ports)


def create_guacamole_connection(
    auth_token, work_id, info, params, username, identifier
):
    try:
        if "swcZone" not in params:
            if info["protocol"] == "vnc":
                connection_id = handle_vnc_connection(
                    auth_token, work_id, info, params, username, identifier
                )
            else:
                connection_id = identifier
        else:
            key = f"{work_id}|{identifier}"
            connection_id = mc.get(key)

            if connection_id is None:
                connection_id = create_swl_connection(
                    auth_token, work_id, info, params, username, identifier, key
                )

            if info["protocol"] == "vnc":
                swl_info = get_connection_info(auth_token, GUAC_DATABASE, connection_id)
                swl_params = get_connection_params(
                    auth_token, GUAC_DATABASE, connection_id
                )
                swl_httpLoginFormat = json.loads(swl_params["httpLoginFormat"])
                swl_httpLoginFormat.update(
                    {"fqdn": f'{swl_params["hostname"]}:{swl_params["port"]}'}
                )
                swl_params["httpLoginFormat"] = json.dumps(swl_httpLoginFormat)
                connection_id = handle_vnc_connection(
                    auth_token, work_id, swl_info, swl_params, username, connection_id
                )

        return jsonify({"identifier": connection_id})
    except Exception as e:
        app.logger.exception(e)
        raise


def handle_vnc_connection(auth_token, work_id, info, params, username, identifier):
    work_container = create_service(app.logger, work_id, params["httpLoginFormat"])

    result_create_connection = create_connection(
        token=auth_token,
        database=GUAC_DATABASE,
        info=info,
        params=params,
        type="changepw" if work_id == "changepw" else "session-manager-chrome",
        hostname=work_container,
        port=os.environ.get("VNC_PORT"),
        origin_identifier=identifier,
        password=os.environ.get("VNC_PASSWORD"),
    )

    assign_user_to_connection(
        auth_token,
        GUAC_DATABASE,
        username,
        result_create_connection["identifier"],
    )
    app.logger.info(
        f"{work_container}: Created VNC connection object to Guacamole successfully"
    )

    return result_create_connection["identifier"]


def create_swl_connection(auth_token, work_id, info, params, username, identifier, key):
    # swczone = get_swczone(params["swcZone"])
    # uids = swczone["swConnector"]
    uids = params["swcZone"].split(",")
    random.shuffle(uids)
    ports = set(mc.get("ports") or [])
    unavailable_ports = set(UNAVAILABLE_PORTS.split(","))
    success = False
    random_port = None

    for uid in uids:
        random_port = get_available_port(ports, unavailable_ports)
        if random_port is None:
            continue

        res = open_port(uid, random_port, params["hostname"], int(params["port"]))

        if res.status_code == requests.codes.ok:
            app.logger.info(f"Succeeded to open port for sw-listener: {random_port}")
            mc.append("ports", random_port)
            success = True
            break
        else:
            continue

    if not success:
        raise RuntimeError(
            "Failed to open port for sw-listener with all available UIDs"
        )
    try:
        check_connection(app.logger, SW_LISTENER, random_port)
    except Exception:
        logging.error("Failed to check connection to SW_LISTENER")
        close_port(random_port)
        raise

    response_generate_auth_token = generate_auth_token()
    auth_token = response_generate_auth_token["authToken"]

    result_create_connection = create_connection(
        token=auth_token,
        database=GUAC_DATABASE,
        info=info,
        params=params,
        type="changepw" if work_id == "changepw" else "session-manager",
        hostname=SW_LISTENER,
        port=random_port,
        origin_identifier=identifier,
    )

    assign_user_to_connection(
        auth_token,
        GUAC_DATABASE,
        username,
        result_create_connection["identifier"],
    )

    app.logger.info("Created connection object to Guacamole successfully")

    all_keys = mc.get("all_keys") or []
    if key not in all_keys:
        all_keys.append(key)
        mc.set("all_keys", all_keys)

    mc.set(key, result_create_connection["identifier"])

    return result_create_connection["identifier"]


@app.route("/create", methods=["POST"])
def create():
    try:
        work_id = request.json["work_id"]
        worker_token = request.json["worker_token"]
        identifier = request.json["identifier"]

        auth_token = generate_auth_token()["authToken"]
        user = get_user(worker_token)
        username = user["username"]
        work = get_work_from_identifier(worker_token, GUAC_DATABASE, work_id)
        info = get_connection_info(auth_token, GUAC_DATABASE, identifier)
        params = get_connection_params(auth_token, GUAC_DATABASE, identifier)

        check_worker_permissions(username, work)
        check_working_hours(username, work)

        return create_guacamole_connection(
            auth_token, work_id, info, params, username, identifier
        )

    except PermissionError as e:
        app.logger.warning(e)
        return jsonify({"error_message": str(e)}), 403
    except ValueError as e:
        app.logger.warning(e)
        return jsonify({"error_message": str(e)}), 400
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error_message": "Internal Server Error"}), 500
