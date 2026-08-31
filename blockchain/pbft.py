import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class PBFTValidator:
    def __init__(self, validator_nodes, quorum_size=None):
        self.validator_nodes = list(validator_nodes)
        self.quorum_size = quorum_size or ((len(self.validator_nodes) * 2) // 3 + 1)

    def _proposal_bytes(self, proposal):
        if isinstance(proposal, (bytes, bytearray)):
            return bytes(proposal)
        if isinstance(proposal, str):
            return proposal.encode('utf-8')
        return json.dumps(proposal, sort_keys=True, default=str).encode('utf-8')

    def _public_key_for_node(self, node_id):
        for candidate in self.validator_nodes:
            if isinstance(candidate, dict):
                candidate_id = candidate.get('node_id') or candidate.get('id')
                if candidate_id == node_id:
                    public_key = candidate.get('public_key')
                    if public_key is None:
                        return None
                    if isinstance(public_key, str):
                        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
                    return public_key
            if getattr(candidate, 'node_id', None) == node_id:
                return candidate.public_key
        return None

    def validate_proposal(self, proposal, signatures):
        if signatures is None:
            signatures = {}
        verified = {}
        for node_id, signature in signatures.items():
            public_key = self._public_key_for_node(node_id)
            if public_key is None:
                continue
            signature_value = signature
            if isinstance(signature, dict):
                signature_value = signature.get('signature') or signature.get('sig') or signature.get('value')
            try:
                public_key.verify(signature_value, self._proposal_bytes(proposal))
            except (TypeError, ValueError, InvalidSignature):
                continue
            verified[node_id] = signature_value
        return len(verified) >= self.quorum_size
