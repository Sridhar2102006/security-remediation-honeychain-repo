
import hashlib
import threading


class BlockchainLedger:
    def __init__(self, initial_chain=None):
        self.chain = list(initial_chain or [])
        self.lock = threading.Lock()

    def add_block(self, block):
        with self.lock:
            previous_hash = self.chain[-1]['hash'] if self.chain else '0' * 64
            block = dict(block)
            block.setdefault('index', len(self.chain))
            block['previous_hash'] = previous_hash
            block_hash = hashlib.sha256((str(previous_hash) + str(block)).encode('utf-8')).hexdigest()
            record = {'block': block, 'hash': block_hash}
            self.chain.append(record)
            return record
