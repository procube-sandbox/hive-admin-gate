#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018 Procube Co., Ltd.

import connexion
import os
import logging
import json
import subprocess
import tempfile
import time
import datetime
import requests
import re
import yaml

from task_executer.models.request_body import RequestBody  # noqa: E501
from task_executer.models.response_body import ResponseBody  # noqa: E501
from distutils.util import strtobool
# from swagger_server import util

logging.basicConfig(level=(logging.DEBUG if strtobool(os.environ.get('IDMTE_DEBUG', 'False')) else logging.INFO))

PLAY_RE = re.compile(r'^PLAY \[([^\]]*)\] \*+$')
TASK_RE = re.compile(r'^TASK \[([^\]]*)\] \*+$')
PLAY_RECAP_RE = re.compile(r'^PLAY RECAP \*+$')


def run_stdout_json(args, env):
  proc = subprocess.run(args, capture_output=True, text=True, env={**os.environ, **env})
  (text_output, _, json_output) = proc.stdout.rpartition('=== END OF TEXT OUTPUT ===:\n')
  try:
    result = json.loads(json_output)
  except ValueError as err:
    # when error occured, stdout is not valid as json
    result = {}
    logging.getLogger('AnsibleTaskExecuter').error(f'fail to parse command stdout as json data:\n{ proc.stdout }\nerror:\n{ err }')
  return (result, proc.returncode, text_output, proc.stderr)

def safe_timestamp(isostr):
  if isostr:
    return datetime.datetime.fromisoformat(isostr.replace('Z', '+00:00'))
  return datetime.datetime.now()

class IDMLogger:
  def __init__(self, codebase, taskId, provSettingName, class_name, playbook, userid='IDM_STAFF_REGISTER', baseurl='http://localhost:8090/IDManager/_taskLogAppender'):
    self.codebase = codebase
    self.logtemplate = dict(taskId=taskId, provSettingName=provSettingName)
    self.userid = userid
    self.url = baseurl + '?_ignoreWarning=true'
    self.contexttemplate = dict(class_name=class_name, playbook=playbook)

  def _post2idm(self, data):
    headers = {'http_systemaccount': self.userid}
    response = requests.post(self.url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

  def _sendTaskLog(self, timestamp, level, code, context):
    log = self.logtemplate.copy()
    log["code"] = str(self.codebase + code)
    log["level"] = level
    log["timestamp"] = timestamp.replace(microsecond=0).isoformat()
    log["context"] = json.dumps(dict(context, **self.contexttemplate))
    return self._post2idm(log)

  def send_start(self):
    self._sendTaskLog(datetime.datetime.now(), 'INFO', 1, dict())

  def send_error(self, message):
    self._sendTaskLog(datetime.datetime.now(), 'ERROR', 2, dict(message=message))

  def send_end(self):
    self._sendTaskLog(datetime.datetime.now(), 'INFO', 3, dict())

  def send_empty_provisioning(self):
    self._sendTaskLog(datetime.datetime.now(), 'INFO', 4, dict())

  def send_result(self, result):
    for play in result.get('plays', []):
      play_summery = play.get('play', {})
      play_duration = play_summery.get('duration', {})
      self._sendTaskLog(safe_timestamp(play_duration.get('start')), 'INFO', 6, dict(play_name=play_summery.get('name')))
      for task in play.get('tasks', []):
        task_summery = task.get('task', {})
        task_duration = task_summery.get('duration', {})
        self._sendTaskLog(safe_timestamp(task_duration.get('start')), 'INFO', 8, dict(task_name=task_summery.get('name')))
        task_timestamp = safe_timestamp(task_duration.get('end'))
        task_name = task_summery.get('name')
        for host_name, host in task.get('hosts', []).items():
          results = host.get('results')
          if results:
            for result in results:
              message = result.get('failed_when_result', result.get('msg'))
              if result.get('failed'):
                self._sendTaskLog(task_timestamp, 'ERROR', 10, dict(task_name=task_name,
                  host_name=host_name, item=json.dumps(result.get('item')), message=': ' + str(message) if message else ''))
              elif result.get('skipped'):
                self._sendTaskLog(task_timestamp, 'INFO', 11, dict(task_name=task_name,
                  host_name=host_name, item=json.dumps(result.get('item'))))
              elif result.get('changed'):
                self._sendTaskLog(task_timestamp, 'INFO', 12, dict(task_name=task_name,
                  host_name=host_name, item=json.dumps(result.get('item'))))
              else:
                self._sendTaskLog(task_timestamp, 'INFO', 13, dict(task_name=task_name,
                  host_name=host_name, item=json.dumps(result.get('item'))))
          else:
            message = host.get('failed_when_result', host.get('msg'))
            if host.get('failed'):
              self._sendTaskLog(task_timestamp, 'ERROR', 14, dict(task_name=task_name,
                host_name=host_name, message=': ' + str(message) if message else ''))
            elif host.get('skipped'):
              self._sendTaskLog(task_timestamp, 'INFO', 15, dict(task_name=task_name,
                host_name=host_name))
            elif host.get('changed'):
              self._sendTaskLog(task_timestamp, 'INFO', 16, dict(task_name=task_name,
                host_name=host_name))
            else:
              self._sendTaskLog(task_timestamp, 'INFO', 17, dict(task_name=task_name,
                host_name=host_name))
        self._sendTaskLog(safe_timestamp(task_duration.get('end')), 'INFO', 9, dict(task_name=task_summery.get('name')))
      self._sendTaskLog(safe_timestamp(play_duration.get('end')), 'INFO', 7, dict(play_name=play_summery.get('name')))
    self._sendTaskLog(datetime.datetime.now(), 'INFO', 5, dict(stats=json.dumps(result.get('stats'))))


class AnsibleExecuter:
  def __init__(self, req):
    self.logger = logging.getLogger(f'AnsibleTaskExecuter')
    self.req : RequestBody = req

  def parse(self, operations):
    self.prov_data = []
    for operation in operations:
      assert operation._class == self.support_class, f'class of operation {operation._class} does not match support class {self.support_class}'
      data = json.loads(operation.value if operation.op_code != 'delete' else operation.before_value)
      data['prov_operation'] = operation.op_code
      self.prov_data.append(data)

  def run_playbook(self, playbook):
    if len(self.prov_data) > 0:
      self.logger.info(f'process provisioning data for {self.support_class} count={len(self.prov_data)}')
      with tempfile.NamedTemporaryFile(mode='w+t') as inventory_file:
        json.dump(self.prov_data, inventory_file)
        inventory_file.flush()
        env = {'IDM_IFFILE_' + self.support_class: inventory_file.name}
        args = ['/root/prov/bin/ansible-playbook']
        # we cannot split debug messsage and result json
        # if self.logger.getEffectiveLevel() < logging.INFO:
        #   args.append('-vvv')
        if strtobool(os.environ.get('ANSIBLE_CHECKMODE', 'False')):
          args.append('-C')
        args.append(f'playbooks/{playbook}')
        self.logger.debug(f'commnad={args}, env={env}')
        (result, exit_code, text_output, stderr) = run_stdout_json(args, env)
        self.idm_logger.send_result(result)
        self.logger.debug(f'ansible-playbook result:\n{yaml.dump(result, allow_unicode=True)}{"text: " + text_output if text_output != "" else "" }{" error: " + stderr if stderr != "" else ""}\nexit code: {exit_code}')
        if exit_code !=0 :
          raise Exception(f'exit code {exit_code} of ansible-playbook command is not 0. {"stderr=" + stderr if stderr != "" else ""}')
    else:
      self.idm_logger.send_empty_provisioning()
  
  def execute(self):
    self.task_id = self.req.task_operation.id
    prov_setting_name = self.req.prov_setting.name
    class_list = list(self.req.class_definition.keys())
    assert len(class_list) == 1, 'class_definition of request must have just one class'
    self.support_class = class_list[0]
    playbook = playbook_map.get(prov_setting_name, {}).get(self.support_class, "")
    assert playbook != "", f'playbook for class "{self.support_class}" in prov setting "{prov_setting_name}" is not registered'
    self.idm_logger = IDMLogger(8200, self.task_id, prov_setting_name, self.support_class, playbook)
    try:
      self.logger.info(f'=== START task id: {self.task_id} at {time.strftime("%Y-%m-%d %H:%M:%S %z")} ===')
      self.parse(self.req.task_operation.operations)
      self.idm_logger.send_start()
      self.run_playbook(playbook)
      self.idm_logger.send_end()
      self.logger.info(f'=== END task id: {self.task_id} at {time.strftime("%Y-%m-%d %H:%M:%S %z")} ===')
    except Exception as err:
      self.logger.exception(f'=== ERROR task id: {self.task_id} at {time.strftime("%Y-%m-%d %H:%M:%S %z")} : {err} ＝＝＝')
      self.idm_logger.send_error(str(err))
      return ('failed', str(err))
    return ('completed', f'task id: {self.task_id} end at {time.strftime("%Y-%m-%d %H:%M:%S %z")}')

file_dir = os.path.dirname(os.path.abspath(__file__))
playbook_map_path = os.path.normpath(os.path.join(file_dir, '../playbook-map.yml'))
with open(playbook_map_path, 'r') as yml:
  playbook_map = yaml.safe_load(yml)

def execute_task(body):  # noqa: E501
  if connexion.request.is_json:
    logging.getLogger(f'AnsibleTaskExecuter').debug(yaml.dump(connexion.request.get_json(), allow_unicode=True))
    result, failed_data = AnsibleExecuter(RequestBody.from_dict(connexion.request.get_json())).execute()  # noqa: E501
    return ResponseBody(result=result, failed_data=failed_data)

  assert False, 'request body must be json'
