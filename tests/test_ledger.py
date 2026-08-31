
from blockchain.ledger import BlockchainLedger


def test_add_block_hashes_chain():
    ledger = BlockchainLedger()
    first = ledger.add_block({'batch_id': 'B-1'})
    second = ledger.add_block({'batch_id': 'B-2'})
    assert first['hash'] != second['hash']
    assert len(ledger.chain) == 2
