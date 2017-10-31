import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # Create the genesis block.
        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof, previous_hash=None):
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

    def register_node(self, address):
        """
        Add a new Node to the list of Nodes.

        :param address: <str> URL of the Node. e.g. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def validate_chain(self, blocks):
        """
        Validate that a given Blockchain is valid.

        :param blocks: <list> A list of the Blocks in a Blockchain.
        :return: <bool> True if valid, False if not.
        """

        last_block = blocks[0]
        current_index = 1
        while current_index < len(blocks):
            block = blocks[current_index]

            # Validate the hash.
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Validate the Proof of Work.
            if not self.validate_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        The Consensus algorithm. Conflicts are resolved by preferring the longest valid chain.
        If another chain in the network is longer, replace our chain with it.

        :return: <bool> True if our chain was replaced, False if not.
        """

        new_chain = None
        current_length = len(self.chain)

        # Look for valid chains which are longer than ours.
        for node in self.nodes:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                response_json = response.json()
                length = response_json['length']
                chain = response_json['chain']

                if length > current_length and self.validate_chain(chain):
                    new_chain = chain
                    current_length = length

        # Replace our chain if we found one which was longer than ours.
        if new_chain:
            self.chain = new_chain
            return True

        return False


# Instantiate our Node.
app = Flask(__name__)

# Generate a globally unique address for this node.
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain.
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # Run the Proof of Work algorithm to get the next proof.
    last_proof = blockchain.last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    # Create the new Block by adding it to the chain.
    block = blockchain.new_block(proof)

    response = {
        'message': "New Block created",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POSTed data.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return f'Missing one or more required values: {required}', 400

    # Create a new Transaction.
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    nodes = request.get_json()['nodes']

    if not nodes:
        return "Error: Please supply a valid list of Nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'all_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def resolve_conflicts():
    chain_replaced = blockchain.resolve_conflicts()

    if chain_replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'new_chain': blockchain.chain
        }

    return jsonify(response), 200


# Start the server if the script is run.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
