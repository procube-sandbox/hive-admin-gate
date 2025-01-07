import docker
import os
import datetime
import logging
from access_guacamole import generate_auth_token, get_all_works
from insert_hosts import insert_hosts

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # ログレベルを設定

# コンソール出力用ハンドラを作成
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # ハンドラのログレベルを設定

# ハンドラをロガーに追加
logger.addHandler(console_handler)
GUAC_DATABASE = os.environ.get("GUAC_DATABASE")

logger.info("Started cleaning davfs volumes")

auth_token = generate_auth_token()["authToken"]
works = get_all_works(auth_token, GUAC_DATABASE)
today = datetime.datetime.today()

tls_config = docker.tls.TLSConfig(
    ca_cert="/root/.docker/ca.pem",
    verify=True,
    client_cert=("/root/.docker/cert.pem", "/root/.docker/key.pem"),
)

base_urls = []
insert_hosts(base_urls)

for base_url in base_urls:
    client = docker.APIClient(base_url=base_url, tls=tls_config)
    filters = {"driver": "fentas/davfs:latest"}
    davfs_volumes = client.volumes(filters=filters)

    for davfs_volume in davfs_volumes["Volumes"]:
        try:
            davfs_volume_name = davfs_volume["Name"]
            davfs_volume_name_list = davfs_volume_name.split("-")
            davfs_volume_work_id = davfs_volume_name_list[2]

            if davfs_volume_work_id == "public":
                break

            for v in reversed(works.values()):
                if v["idmIdentifier"] == davfs_volume_work_id:
                    rm_flag: bool = True
                    for period in v["periods"]:
                        valid_until_date = datetime.datetime.strptime(
                            period["validUntil"], "%Y-%m-%d"
                        )
                        if valid_until_date > today:
                            rm_flag = False
                            break
                    if rm_flag:
                        client.remove_volume(davfs_volume_name, force=True)
                        logger.info(davfs_volume_name + " Deleted. HOST:" + base_url)

                    break

        except Exception as e:
            print(e)
            continue

logger.info("Ended cleaning davfs volumes")
