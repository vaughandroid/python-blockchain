import hashlib
import json
from time import time

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Create the genesis block.
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain.

        :param proof: <int> The proof given by the Proof of Work algorithm.
        :param previous_hash: (Optional) <str> Hash of previous Block.
        :return: <dict> The new Block.
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.last_block)
        }
        self.chain.append(block)
        self.current_transactions = []
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block.

        :param sender: <str> Address of the sender
        :param recipient: <str> Address of the recipient.
        :param amount: <int> Transaction amount.
        :return: The index of the Block that will hold this transaction.
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block.

        :param block: <dict> Block to hash.
        :return: <str> SHA-256 hash of the Block.
        """

        # Order the keys to ensure consistent hashing.
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """
        The most recently added Block in the Blockchain.

        :return: <dict> The Block.
        """
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work algorithm:
        - Find a number p' such that hash(pp') contains 4 leading zeroes.
        - p is the previous proof, and p' is the new proof.

        :param last_proof: <int>
        :return: <int> The new proof.
        """

        proof = 0
        while self.validate_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def validate_proof(last_proof, proof):
        """
        Validates a Proof: i.e. hash(last_proof, proof) contains 4 leading zeroes.

        :param last_proof: <int> Previous Proof.
        :param proof: <int> Proof to be validated.
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"