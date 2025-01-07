#! /bin/sh

PROXY_IP=""
STAGE=""
HIVE_NAME="nsag-dev"

echo "http_proxy=http://$PROXY_IP:3128" > /etc/environment
echo "HTTP_PROXY=http://$PROXY_IP:3128" >> /etc/environment
echo "https_proxy=http://$PROXY_IP:3128" >> /etc/environment
echo "HTTPS_PROXY=http://$PROXY_IP:3128" >> /etc/environment
echo "no_proxy=${STAGE}hive0.$HIVE_NAME,${STAGE}hive1.$HIVE_NAME,${STAGE}hive2.$HIVE_NAME,${STAGE}hive3.$HIVE_NAME,localhost,127.0.0.1" >> /etc/environment
echo "NO_PROXY=${STAGE}hive0.$HIVE_NAME,${STAGE}hive1.$HIVE_NAME,${STAGE}hive2.$HIVE_NAME,${STAGE}hive3.$HIVE_NAME,localhost,127.0.0.1" >> /etc/environment