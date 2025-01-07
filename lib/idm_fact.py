#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Mitsuru Nakakawaji <mitsuru@procube.jp>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# TODO: METADATA, DOCUMENT, EXAMPLE should be written
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#ansible-metadata-block

# to test this module
# ansible -m idm_fact -M . -c docker -i ,idm -a 'interface=_classes/_classDefinition' idm
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible.module_utils.six.moves.urllib.parse import urlencode
import json

class IDM_facts(AnsibleModule):
  def __init__(self):
    argument_spec = dict(
      interface=dict(required=True),
      host=dict(required=False,default='localhost'),
      port=dict(required=False,type='int',default=8090),
      system_account=dict(required=False,default='IDM_AUTO_BUILDER'),
      filter=dict(required=False,type='dict'),
      properties=dict(required=False,type='list',elements='str')
    )
    super(IDM_facts, self).__init__(argument_spec=argument_spec, supports_check_mode=True)

  def process_task(module):
    params = {}
    if module.params['filter']:
      params['_filter'] = module.jsonify(module.params['filter'])
    if module.params['properties']:
      params['_properties'] = ','.join(module.params['properties'])
    module.params['validate_certs'] = False

    result = module.call_idm(params, 'GET')

    for instance in result:
      instance.pop('_csn', None)
    return result

  def call_idm(module, params, method = 'GET', key = '', data = {}, interface = ''):
    if not interface:
      interface = module.params['interface']
    url = 'http://' + module.params['host'] + ':' + str(module.params['port']) + '/IDManager/' + interface
    if key:
      url += '/' + key
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
      raise StandardError('Failed to execute the API request: {0}: {1}'.format(
        info['msg'], json.dumps(body, ensure_ascii=False)))
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
  idm_facts = IDM_facts()
  try:
    result = idm_facts.process_task()
  except Exception as e:
    idm_facts.fail_json(msg=str(e))
    # never reach here
  idm_facts.exit_json(result=result)
  # never reach here

if __name__ == '__main__':
  main()