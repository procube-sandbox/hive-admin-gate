import docker
import os
import uuid
import threading
import logging
from check_connection import check_connection
from insert_hosts import insert_hosts


def create_client(logger: logging.Logger, base_urls: list[str]) -> docker.APIClient:
    tls_config = docker.tls.TLSConfig(
        ca_cert="/root/.docker/ca.pem",
        verify=True,
        client_cert=("/root/.docker/cert.pem", "/root/.docker/key.pem"),
    )
    for base_url in base_urls:
        try:
            client = docker.APIClient(base_url=base_url, tls=tls_config)
            logger.info("docker host is " + base_url)
            return client
        except Exception as e:
            logger.warning(e)
            continue


def create_service(logger: logging.Logger, work_id: str, http_login_format: str) -> str:
    lock = threading.Lock()

    # 環境変数取得
    webdav_server = os.environ.get("WEBDAV_SERVER")
    webdav_port = os.environ.get("WEBDAV_PORT")
    webdav_password = os.environ.get("WEBDAV_PASSWORD")

    image_chrome = "procube/node-chrome"
    swarm_network = ["hive_default_network"]

    base_urls = []
    insert_hosts(base_urls)
    client = create_client(logger, base_urls)

    work_container = "chrome-" + work_id + "-" + str(uuid.uuid4())

    http_login_format_env = "HTTP_LOGIN_FORMAT=" + http_login_format
    selenium_env = [http_login_format_env]

    def driver_config(work_id: str):
        url = f"http://{webdav_server}:{webdav_port}/{work_id}/"
        return docker.types.services.DriverConfig(
            "fentas/davfs",
            options={"username": work_id, "password": webdav_password, "url": url},
        )

    davfs_work_mount = docker.types.Mount(
        f"/mnt/{work_id}",
        f"davfs-volume-{work_id}",
        type="volume",
        driver_config=driver_config(work_id),
    )
    davfs_public_mount = docker.types.Mount(
        "/mnt/public",
        "davfs-volume-public",
        type="volume",
        driver_config=driver_config("public"),
    )
    shm_mount = docker.types.Mount("/dev/shm", "/dev/shm", type="bind")

    container_spec = docker.types.ContainerSpec(
        image_chrome,
        hostname=work_container,
        env=selenium_env,
        mounts=[davfs_work_mount, davfs_public_mount, shm_mount],
        cap_add=["NET_ADMIN"],
    )
    task_tmpl = docker.types.TaskTemplate(container_spec)
    try:
        if lock.locked():
            logger.warning(
                work_container
                + ": Other process threading lock. Please wait for a while"
            )
        lock.acquire()
        logger.info(work_container + ": Create process lock acquired")

        client.create_service(
            task_tmpl,
            name=work_container,
            networks=swarm_network,
            endpoint_spec=docker.types.EndpointSpec(mode="dnsrr"),
        )
        logger.info(work_container + ": Create successfully")
    except Exception as e:
        raise e
    finally:
        lock.release()
    logger.info(work_container + ": Create process lock released")

    check_connection(logger, work_container, 5900)
    return work_container


def delete_service(logger: logging.Logger, work_container: str) -> None:
    base_urls = []
    insert_hosts(base_urls)
    client = create_client(logger, base_urls)
    client.remove_service(work_container)
    logger.info(work_container + ": Delete successfully")
    logger.info(
        work_container + ": Delete VNC connection object from guacamole successfully"
    )
    return
