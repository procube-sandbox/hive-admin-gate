#! /bin/bash

# scpでlatestのバックアップを/home/admin/backup配下に置く
# for name in backup-idm-latest.tar.gz backup-idm_eu_app_csv-latest.tar.gz  backup-ldap-latest.ldif backup-ldap_config-latest.ldif backup-amdb-latest.sql.gz backup-guacamole_db-latest.sql.gz backup-mongo-backup-latest.tar.gz
# do
#   scp /home/admin/$name:/home/admin/$name
# done

for SERVICE in idm ldap amdb postgres mongo
do
  hive-backup.sh -l $SERVICE -r
done