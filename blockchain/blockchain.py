import binascii
import hashlib
from collections import OrderedDict
from time import time
from urllib.parse import urlparse
from uuid import uuid4
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests

MINNEUR = "ECOSYSTEME"
RECOMPENSE_MINNEUR = 100
DIFFICULTE = 3


class Blockchain:

    def __init__(self):
        self.transactions = []
        self.chain = []  # chaine de block
        self.noeuds = set()
        # affecter un id unique et aleatoire pour chaque noeuds
        self.id_noeud = str(uuid4()).replace('-', '')
        # Creation du premier block le genesis
        self.cree_block(0, '00')

    def registe_noeud(self, noeud_url):
        # ajouter un nouveau noed a la liste des noeds

        parse_url = urlparse(noeud_url)
        if parse_url.netloc:
            self.noeuds.add(parse_url.netloc)

        else:
            raise ValueError('Invalid URL')

    def cree_block(self, nonce, hash_precedent):  # fonction permet de cree un nouveau block
        # l'ajout des transaction au nouveau block
        block = {'num_block': len(self.chain) + 1,
                 'timestamp': time(),
                 'transactions': self.transactions,
                 'nonce': nonce,
                 'hash_precedent': hash_precedent}

        # vider le tableau des transactions
        self.transactions = []
        # ajouter le nouveau block a la chaine
        self.chain.append(block)
        return block

    def hash(self, block):  # fonction permet de hasher un block
        # hasher le block

        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def preuve_de_travail(self):
        # preuve de travail
        dernier_block = self.chain[-1]
        last_hash = self.hash(dernier_block)

        nonce = 0
        while self.valid_proof(self.transactions, last_hash, nonce) is False:
            nonce += 1

        return nonce

    # cete algorithme recherche un nonce qui satisfait la condition d'exploration de donnees
    def valid_proof(self, transactions, last_hash, nonce, difficulte=DIFFICULTE):
        # verifier si la peuve de travail est valide
        contenu_b = (str(transactions) + str(last_hash) + str(nonce)).encode()
        contenu_b_hash = hashlib.sha256(contenu_b).hexdigest()
        return contenu_b_hash[:difficulte] == '0' * difficulte

    def valid_chain(self, chain):
        # verifier la validité de la chain cote hash precedent et structure de transaction
        dernier_block = chain[0]
        index_courant = 1

        while index_courant < len(chain):
            block = chain[index_courant]
            # verification du hash du block precedent
            if block['hash_precedent'] != self.hash(dernier_block):
                return False

            transactions = block['transactions'][:-1]  # la transaction de recompensation a ne pas tester
            # verifier le dictionnaire des transaction
            transaction_elements = ['Cle_Public_Emetteur', 'Cle_Public_recepteur', 'valeur']
            transactions = [OrderedDict((k, transaction[k]) for k in transaction_elements) for transaction in
                            transactions]

            if not self.valid_proof(transactions, block['hash_precedent'], block['nonce'], DIFFICULTE):
                return False
            dernier_block = index_courant
            index_courant = index_courant + 1
        return True

    def verifier_transaction_signature(self, Cle_Public_Emetteur, signature, transaction):
        # verifier si la signature est satisfaisante
        cle_public = RSA.importKey(binascii.unhexlify(Cle_Public_Emetteur))
        verifier = PKCS1_v1_5.new(cle_public)
        h = SHA.new(str(transaction).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(signature))

    def tester_transaction(self, Cle_Public_Emetteur, Cle_Public_recepteur, valeur, signature):
        # ajouter chaque nouvelle transaction au tableau des transactions valide si la signature est valide ss
        transaction = OrderedDict({'Cle_Public_Emetteur': Cle_Public_Emetteur,
                                   'Cle_Public_recepteur': Cle_Public_recepteur,
                                   'valeur': valeur})

        # recompensation du noued
        if Cle_Public_Emetteur == MINNEUR:
            self.transactions.append(transaction)
            return len(self.chain) + 1

        else:
            transaction_verification = self.verifier_transaction_signature(Cle_Public_Emetteur, signature, transaction)
            if transaction_verification:

                self.transactions.append(transaction)
                return len(self.chain) + 1
            else:
                return False

    def resoudre_conflit(self):
        # resoudre le probleme entre les noeuds concernnant la chaine la plus long
        liste_noeuds = self.noeuds
        nouvelle_chaine = None
        # intialiser la chain
        max_length = len(self.chain)

        # comparer la chaine avec toutes celles du reseau
        for noeud in liste_noeuds:
            print('http://' + noeud + '/chain')
            response = requests.get('http://' + noeud + '/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    nouvelle_chaine = chain

        # remplacer la chaine avec la nouvelle
        if nouvelle_chaine:
            self.chain = nouvelle_chaine
            return True

        return False


# initialisation de l'app
app = Flask(__name__)

# initialisation de la blockchain
blockchain = Blockchain()
CORS(app)


@app.route('/')
def index():
    return render_template('./aceuille.html')


@app.route('/index')
def indexe():
    return render_template('./index.html')


@app.route('/configure')
def configure():
    return render_template('./configure.html')


"""cette api permet d'ajouter une transaction a la liste des transaction qui seront ajouter au block si la signature 
 est valide """


@app.route('/transactions', methods=['POST'])
def nouvelle_transaction():
    valeurs = request.form

    # verifier si tous les champs existe
    requete = ['Cle_Public_Emetteur', 'Cle_Public_recepteur', 'montant', 'signature']
    if not all(k in valeurs for k in requete):
        return 'Valeurs manquantes', 400

    transaction_result = blockchain.tester_transaction(valeurs['Cle_Public_Emetteur'], valeurs['Cle_Public_recepteur'],
                                                       valeurs['montant'], valeurs['signature'])

    if transaction_result == False:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        response = {'message': 'Transaction sera ajouter au blocks ' + str(transaction_result)}
        return jsonify(response), 201


# cette api renvoie toutes les donnees de la chaine de block
@app.route('/chain', methods=['GET'])
def chaine_complete():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


# cette api execute l'algorithme de preuve de travail et ajoute le nouveau block de transaction a la blockchain
@app.route('/mine', methods=['GET'])
def mine():
    # executer l'algorithme preuve de travail
    dernier_block = blockchain.chain[-1]
    nonce = blockchain.preuve_de_travail()

    # recompencer le mineur
    blockchain.tester_transaction(Cle_Public_Emetteur=MINNEUR, Cle_Public_recepteur=blockchain.id_noeud,
                                  valeur=RECOMPENSE_MINNEUR, signature="")

    # recuperer le dernier block dans le precedent_hash et ajouter le nouveau block a la chain
    hash_precedent = blockchain.hash(dernier_block)
    block = blockchain.cree_block(nonce, hash_precedent)

    response = {
        'message': "Nouveau bloc forgé",
        'num_block': block['num_block'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'hash_precedent': block['hash_precedent'],
    }
    return jsonify(response), 200


# cette api renvoies toutes les transactions pour les afficher dans le mempol
@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    # recuperer la transaction du mempol
    transactions = blockchain.transactions

    response = {'transactions': transactions}
    return jsonify(response), 200


# cette api prend une listes de url noeuds et les ajoute a la liste des noeuds
@app.route('/noeuds/registre', methods=['POST'])
def registes_noeudes():
    values = request.form
    noeuds = values.get('noeuds').replace(" ", "").split(',')

    if noeuds is None:
        return "Error: Veuillez fournir une liste valide de noeuds", 400

    for node in noeuds:
        blockchain.registe_noeud(node)

    response = {
        'message': 'De nouveaux noeuds ont été ajoutés',
        'total_noeuds': [node for node in blockchain.noeuds],
    }
    return jsonify(response), 201


# cette api renvoie la listes des noeuds
@app.route('/noeuds/get', methods=['GET'])
def get_noeuds():
    noeuds = list(blockchain.noeuds)
    response = {'noeuds': noeuds}
    return jsonify(response), 200


# cette api resout le conflits entre les noeuds
@app.route('/noeuds/resolution', methods=['GET'])
def consensus():
    remplacer = blockchain.resoudre_conflit()

    if remplacer:
        response = {
            'message': 'Notre chaîne a été remplacée',
            'nouvelle_chaine': blockchain.chain
        }
    else:
        response = {
            'message': 'Notre chaîne fait autorité',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port, debug=True)
