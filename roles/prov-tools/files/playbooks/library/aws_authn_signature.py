# coding: utf-8
#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
import hashlib
import hmac

def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(("AWS4" + key).encode("utf-8"), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, "aws4_request")
    return kSigning

def main():
    module = AnsibleModule(
        argument_spec=dict(
            key=dict(
                type="str",
                required=True
            ),
            dateStamp=dict(
                type="str",
                required=True
            ),
            regionName=dict(
                type="str",
                required=True
            ),
            serviceName=dict(
                type="str",
                required=True
            ),
            stringToSign=dict(
                type="str",
                required=True
            )
        )
    )
    pKey = module.params["key"]
    pDateStamp = module.params["dateStamp"]
    pRegionName = module.params["regionName"]
    pServiceName = module.params["serviceName"]
    pStringToSign = module.params["stringToSign"]

    # Sign the string    
    signing_key = getSignatureKey(pKey, pDateStamp, pRegionName, pServiceName)
    signature = hmac.new(signing_key, (pStringToSign).encode('utf-8'), hashlib.sha256).hexdigest()    

    module.exit_json(changed=False, reply=signature)

if __name__ == "__main__":
    main()
