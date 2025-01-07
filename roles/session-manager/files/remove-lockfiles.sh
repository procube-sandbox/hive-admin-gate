#! /bin/ash

find /var/lock/session-manager/ -name '*.lock' -mtime +7 -delete
