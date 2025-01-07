import os
import logging
from access_guacamole import (
    generate_auth_token,
    get_all_connections,
    get_connection_params,
    delete_connection,
)
from access_docker import delete_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # ログレベルを設定

# コンソール出力用ハンドラを作成
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # ハンドラのログレベルを設定

# ハンドラをロガーに追加
logger.addHandler(console_handler)
GUAC_DATABASE = os.environ.get("GUAC_DATABASE")

logger.info("Started cleaning chrome containers")

auth_token = generate_auth_token()["authToken"]
connections = get_all_connections(auth_token, GUAC_DATABASE)

for v in connections.values():
    try:
        if (
            v["idmIdentifier"] == "session-manager-chrome"
            and v["activeConnections"] == 0
        ):
            params = get_connection_params(auth_token, GUAC_DATABASE, v["identifier"])
            logger.info("delete " + params["hostname"])
            delete_service(logger, params["hostname"])
            delete_connection(auth_token, GUAC_DATABASE, v["identifier"])
    except Exception as e:
        logger.error(e)
        continue

logger.info("Ended cleaning chrome containers")
