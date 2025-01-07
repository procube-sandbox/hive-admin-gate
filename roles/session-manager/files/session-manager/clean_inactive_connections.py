import memcache
import os
import logging
from access_guacamole import generate_auth_token, get_all_connections, get_connection_params, delete_connection
from access_swl import close_port

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # ログレベルを設定

# コンソール出力用ハンドラを作成
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # ハンドラのログレベルを設定

# ハンドラをロガーに追加
logger.addHandler(console_handler)

MEMCACHED_URL = os.environ.get("MEMCACHED_URL")
GUAC_DATABASE = os.environ.get("GUAC_DATABASE")

logger.info("Started cleaning inactive connections")

auth_token = generate_auth_token()["authToken"]
connections = get_all_connections(auth_token, GUAC_DATABASE)


def get_all_keys_and_values(mc):
    # キーのリストを取得
    keys = mc.get("all_keys") or []

    # 全てのキーとバリューを取得
    result = {}
    for key in keys:
        value = mc.get(key)
        result[key] = value

    return result


for v in connections.values():
    try:
        mc = memcache.Client([MEMCACHED_URL], debug=0)
        if (
            v["idmIdentifier"] == "session-manager"
            and v["activeConnections"] == 0
        ):
            if not v["identifier"] in get_all_keys_and_values(mc).values():
                logger.info(f"delete {v["name"]}")
                params = get_connection_params(auth_token,GUAC_DATABASE,v["identifier"])
                res = close_port(int(params["port"]))
                if res.status_code == 200:
                    logger.info(f"Closed port {params["port"]} successfully")
                if res.status_code == 404:
                    logger.warning(f"Not found port {params["port"]} task on SWL")
                
                delete_connection(auth_token, GUAC_DATABASE, v["identifier"])
            else:
                logger.info(f"inuse {v["name"]}")
    except Exception as e:
        logger.error(e)
        continue

logger.info("Ended cleaning inactive connections")
