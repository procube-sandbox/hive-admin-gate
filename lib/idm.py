#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Mitsuru Nakakawaji <mitsuru@procube.jp>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# TODO: METADATA, DOCUMENT, EXAMPLE should be written
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#ansible-metadata-block

# to test this module
# ansible -m idm -M . -c docker -i ,idm -a 'interface=_provSetting key_property=name' idm
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.six.moves.urllib.parse import urlencode
from dictdiffer import diff
import json

class IDM(AnsibleModule):
  def __init__(self):
    argument_spec = dict(
      interface=dict(required=True),
      host=dict(required=False,default='localhost'),
      port=dict(required=False,type='int',default=8090),
      system_account=dict(required=False,default='IDM_AUTO_BUILDER'),
      filter=dict(required=False,type='dict'),
      properties=dict(required=False,type='list',elements='str'),
      instances=dict(required=True,type='list',elements='dict'),
      key_property=dict(required=True),
      delete_orphands=dict(required=False,type='bool',default=True),
      state=dict(required=False,default='update', choices=['absent', 'present', 'update'])
    )
    super(IDM, self).__init__(argument_spec=argument_spec, supports_check_mode=True)
    self.changed = False

  def __enter__(self):
    pass

  def __exit__(self, exc_type, exc_value, traceback):
    self.debug("Enter exit handler exc_value={0}".format(exc_value))
    if not self.check_mode:
      try:
        interface = '_currentSandboxProvRequestsUser'
        if self.params['interface'].startswith('_'):
          interface = '_currentRepositorySandboxProvRequestsUser'
        response = self.call_idm({}, interface = interface, key= self.params['system_account'])
        if not response:
          self.debug("No provisioning Request found for {0}.".format(self.params['system_account']))
          return
        request_id = response[0]['id']
      except Exception as e:
        msg = "Fail to get provisiong request for {0}: {1}".format(self.params['system_account'], e)
        if exc_value:
          msg = "Error: {0} and {1}".format(exc_value, msg)
        raise Exception(msg)
      self.debug("Success to get provisiong request for {0} id= {1}".format(self.params['system_account'], request_id))
      try:
        data={'requestId': request_id}
        if exc_value:
          data['cancel'] = True
        response = self.call_idm({}, method='POST', interface = '_editingCompletedEvents', data = data)
      except Exception as e:
        msg = "Fail to commit/cancel provisiong request {0}: {1}".format(data, e)
        if exc_value:
          msg = "Error: {0} and {1}".format(exc_value, msg)
        raise Exception(msg)
      self.debug("Success to commit/cancel provisiong request {0}".format(data))
      if exc_value:
        # success to cancel any change
        self.changed = False

  def process_task(module):
    params = {}
    if module.params['filter']:
      params['_filter'] = module.jsonify(module.params['filter'])
    if module.params['properties']:
      params['_properties'] = ','.join(module.params['properties'])
    module.params['validate_certs'] = False
    key_property = module.params['key_property']

    try:
      before_instances = module.call_idm(params)
    except Exception as e:
      raise Exception("Fail to get before values: {0}".format(e))

    before_map = {}
    for target in before_instances:
      if key_property not in  target:
        raise Exception('Instance {0} from the interface {1} does not have key property {2}, {3}, {4}'.format(
          module.jsonify(target), module.params['interface'], key_property, type(target), target))
      target.pop('_csn', None)
      before_map[target[key_property]] = target

    state = module.params['state']
    module.deleted_list = []
    module.updated_list = []
    module.added_list = []
    for target in module.params['instances']:
      if key_property not in target:
        raise Exception('Instance {0} does not have key property {1}'.format(module.jsonify(target), key_property))
      key =  target[key_property]
      if key in before_map:
        before = before_map.pop(key)
        if state == 'absent':
          action = 'delete "{0}" from {1}'.format(key, module.params['interface'])
          result = 0
          if not module.check_mode:
            try:
              result = module.call_idm(params, method = 'DELETE', key = key)
            except Exception as e:
              raise Exception("Fail to {0}: {1}".format(action, e))
          module.debug('Success to {0} check_mode={2} result={1}'.format(action, module.check_mode, result))
          module.deleted_list.append(key)
        elif state == 'update' and target != before:
          diff_result = diff(target, before)
          action = 'update "{0}" in {1} for differrnece {2}'.format(
            key, module.params['interface'], str(list(diff_result)))
          result = 0
          if not module.check_mode:
            try:
              result = module.call_idm(params, method = 'PUT', key = key, data = target)
            except Exception as e:
              raise Exception("Fail to {0}: {1}".format(action, e))
          module.debug('Success to {0} check_mode={2} result={1}'.format(action, module.check_mode, result))
          module.updated_list.append(key)
      elif state != 'absent':
        action = 'add "{0}" into {1} as {2}'.format(
          key, module.params['interface'], json.dumps(target, ensure_ascii=False))
        result = 0
        if not module.check_mode:
          try:
            result = module.call_idm(params, method = 'POST', data = target)
          except Exception as e:
            raise Exception("Fail to {0}: {1}".format(action, e))
          module.debug('Success to {0} check_mode={2} result={1}'.format(action, module.check_mode, result))
        module.added_list.append(key)
    if before_map and module.params['delete_orphands'] and state != 'absent' :
      for key in before_map:
        action = 'delete orphand "{0}" from {1}'.format(key, module.params['interface'])
        result = 0
        if not module.check_mode:
          try:
            result = module.call_idm(params, method = 'DELETE', key = key)
          except Exception as e:
            raise Exception("Fail to {0}: {1}".format(action, e))
        module.debug('Success to {0} check_mode={2} result={1}'.format(action, module.check_mode, result))
        module.deleted_list.append(key)

  def call_idm(module, params, method = 'GET', key = '', data = {}, interface = ''):
    if not interface:
      interface = module.params['interface']
    url = 'http://' + module.params['host'] + ':' + str(module.params['port']) + '/IDManager/' + interface
    if key:
      url += '/' + str(key)
    if params :
      url += '?' + urlencode(params)

    headers = {'Accept': 'application/json charset=utf-8', 'HTTP_SYSTEMACCOUNT': module.params['system_account']}
    datastr = ''
    if data:
      headers['Content-Type'] = 'application/json'
      datastr = json.dumps(data, ensure_ascii=False)
      module.debug("call idm with body: " + datastr)
    response, info = fetch_url(module, url, method=method, headers=headers, data=datastr)
    body = '"no body data"'
    if response:
      body = response.read()
    elif 'body' in info:
      body = info['body']
    if int(info['status']) != 200:
      body = info.get('body')
      raise Exception('Failed to execute the API request: {0}: {1}'.format(
        info['msg'], body.decode() if type(body) == bytes else str(body)))
    return json.loads(body)

  def exit_process(self):
    changed = len(self.deleted_list) > 0 or len(self.updated_list) > 0 or len(self.added_list) > 0
    self.exit_json(changed=changed,
      added_list=self.added_list, updated_list=self.updated_list, deleted_list=self.deleted_list)
    # never reach here

def _byteify(data, ignore_dicts = False):
    # if this is a unicode string, return its string representation
    if isinstance(data, str):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [ _byteify(item, ignore_dicts=True) for item in data ]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.items()
        }
    # if it's anything else, return it in its original form
    return data


def main():
  idm = IDM()
  try:
    with idm:
      idm.process_task()
  except Exception as e:
    idm.fail_json(msg=str(e))
    # never reach here
  idm.exit_process()
  # never reach here

if __name__ == '__main__':
  main()
