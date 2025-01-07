#!/bin/sh
if [ -n "$(consul kv get --keys)" ]; then
  consul kv export | sed -n 's/"key": "\(.*\)",$/\1/p' | xargs -L 1 consul kv delete
fi
consul kv import -
