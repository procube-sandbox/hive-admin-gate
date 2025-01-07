from ansible.errors import AnsibleError

# ttp、jsonのインポート。インポートに失敗した場合、後続の処理でエラー出力できるようにする。
try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

try:
    import re
    HAS_RE = True
except ImportError:
    HAS_RE = False


class FilterModule(object):

    def metadata2entityid(self, metadata):
        if not HAS_LXML:
            raise AnsibleError('metadata2entityid filter requires lxml library to be installed')

        if not HAS_RE:
            raise AnsibleError('metadata2entityid filter requires re library to be installed')

        metadata = re.sub('^<\\?xml[^>]*\\?>', '', metadata)
        tree = etree.fromstring(metadata)
        entityid = tree.xpath('/md:EntityDescriptor/@entityID', namespaces={'md': 'urn:oasis:names:tc:SAML:2.0:metadata'})

        if len(entityid) == 0:
            raise AnsibleError(f'entityID can not find in metadata {metadata}')

        # return result in JSON format
        results = entityid[0]
        return results

    def filters(self):
        return {
            'metadata2entityid': self.metadata2entityid,
        }