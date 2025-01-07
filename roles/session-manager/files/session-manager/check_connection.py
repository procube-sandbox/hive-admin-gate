import socket
import time


def check_connection(logger, address, port, max_retries=30, delay=1, timeout=15):
    for attempt in range(max_retries):
        try:
            with socket.create_connection((address, port), timeout=timeout):
                logger.info(f"{address}: Connect successfully on attempt {attempt + 1}")
                return address
        except socket.error as e:
            logger.warning(f"{address}: Attempt {attempt + 1} failed with error: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise Exception(
                    f"{address}: Failed to connect after {max_retries} attempts"
                )
