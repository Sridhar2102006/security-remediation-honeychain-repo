
from blockchain.pbft import PBFTValidator


def test_validate_proposal_requires_real_signers_only():
    validator_nodes = [
        {'node_id': 'A', 'public_key': 'f6f367d1d06dff7e7e0d41a42a3cc5d80fb05fd7f0426918f2fe420eeeb54d4d'},
        {'node_id': 'B', 'public_key': '6a0413115fbefc53f7d53f7e57a7e2a91227a429d49a9f6fd59d113d7b5c7d1f'},
        {'node_id': 'C', 'public_key': '1f0cb13d6a9d98b7d40f8df1947a4dddbb3f6bda7ec0af5d790d34d4857e7a7a'},
    ]
    validator = PBFTValidator(validator_nodes)
    assert validator.validate_proposal({'batch_id': 'abc'}, {'A': b'not-real', 'fake': b'not-real'}) is False
