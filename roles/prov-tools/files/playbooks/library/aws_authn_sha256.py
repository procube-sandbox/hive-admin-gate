# coding: utf-8
#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
import hashlib

def main():
    module = AnsibleModule(
        argument_spec=dict(
            item=dict(
                type="str",
                required=True
            )
        )
    )
    item = module.params["item"]
    hashed_item = hashlib.sha256(item.encode('utf-8')).hexdigest()
    module.exit_json(changed=False, reply=hashed_item)

if __name__ == "__main__":
    main()
