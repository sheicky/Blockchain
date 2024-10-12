import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request, render_template_string, render_template
from urllib.parse import urlparse
import requests


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(previous_hash=1, proof=100)
        self.nodes = set()

    def register_node(self, address):
        # Ajout d'un nouveau noeud à la liste
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def proof_of_work(self, last_proof):
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    def new_block(self, proof, previous_hash=None):
        # Création d'un nouveau bloc et ajout à la chaîne
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        # Ajout d'une nouvelle transaction à la liste des transactions
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        # Hachage d'un bloc en utilisant SHA-256
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Retourne le dernier bloc de la chaîne
        return self.chain[-1]

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n--------------\n")

            # Vérification que le hachage du bloc est correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Vérification que la preuve est correcte
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        # Remplacement de notre chaîne par la chaîne la plus longue valide du réseau
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                data = response.json()
                length = data['length']
                chain = data['chain']

                # Vérification si la longueur est plus grande et la chaîne est valide
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Remplacer notre chaîne si nous trouvons une nouvelle chaîne valide plus longue que la nôtre
        if new_chain:
            self.chain = new_chain
            return True

        return False


app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/mine', methods=['GET'])
def mine():
    if not blockchain.current_transactions:
        return render_template_string('''
        <h1>Aucune Transaction à Miner</h1>
        <p>Veuillez créer une transaction avant de miner un bloc.</p>
        <a href="/transactions/new" class="button">Créer une nouvelle transaction</a>
        <a href="/" class="button">Retour à l'accueil</a>
        ''')

    # Exécution de l'algorithme de preuve de travail
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Récompense pour le minage
    blockchain.new_transaction(
        sender="0",  # Cela signifie que ce nœud a miné un nouveau bloc
        recipient=node_identifier,
        amount=1,
    )

    # Création du nouveau bloc
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Nouveau Bloc Forgé",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return render_template_string('''
    <h1>Nouveau Bloc Forgé</h1>
    <p>Index: {{ index }}</p>
    <p>Transactions: {{ transactions }}</p>
    <p>Preuve: {{ proof }}</p>
    <p>Hash Précédent: {{ previous_hash }}</p>
    <a href="/" class="button">Retour à l'accueil</a>
    ''', **response)

@app.route('/transactions/new', methods=['GET', 'POST'])
def new_transaction():
    if request.method == 'GET':
        return '''
        <form action="/transactions/new" method="post">
            Expéditeur: <input type="text" name="sender"><br>
            Destinataire: <input type="text" name="recipient"><br>
            Montant: <input type="number" name="amount"><br>
            <input type="submit" value="Soumettre">
        </form>
        <a href="/" class="button">Retour à l'accueil</a>
        '''
    elif request.method == 'POST':
        values = request.form

        # Vérification que les champs requis sont dans les données POSTées
        required = ['sender', 'recipient', 'amount']
        if not all(k in values for k in required):
            return 'Valeurs manquantes', 400

        # Création d'une nouvelle transaction
        index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
        response = {'message': f'Transaction sera ajoutée au Bloc {index}'}
        return render_template_string('''
        <h1>Transaction Créée</h1>
        <p>{{ message }}</p>
        <a href="/mine" class="button">Miner un nouveau bloc</a>
        <a href="/" class="button">Retour à l'accueil</a>
        ''', **response)

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return render_template('chain.html', chain=response['chain'], length=response['length'])

@app.route('/nodes/register', methods=['GET', 'POST'])
def register_nodes():
    if request.method == 'GET':
        return '''
        <form action="/nodes/register" method="post">
            Noeuds (séparés par des virgules): <input type="text" name="nodes"><br>
            <input type="submit" value="Soumettre">
        </form>
        <a href="/" class="button">Retour à l'accueil</a>
        '''
    elif request.method == 'POST':
        values = request.form

        nodes = values.get('nodes')
        if nodes is None:
            return "Erreur: Veuillez fournir une liste valide de noeuds", 400

        nodes = nodes.split(',')
        for node in nodes:
            blockchain.register_node(node.strip())

        response = {
            'message': 'Nouveaux noeuds ont été ajoutés',
            'total_nodes': list(blockchain.nodes)
        }
        return render_template_string('''
        <h1>Noeuds Enregistrés</h1>
        <p>{{ message }}</p>
        <p>Noeuds Totaux: {{ total_nodes }}</p>
        <a href="/" class="button">Retour à l'accueil</a>
        ''', **response)

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Notre chaîne a été remplacée',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Notre chaîne est autoritaire',
            'chain': blockchain.chain
        }

    return render_template_string('''
    <h1>Consensus</h1>
    <p>{{ message }}</p>
    <pre>{{ chain }}</pre>
    <a href="/" class="button">Retour à l'accueil</a>
    ''', **response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)