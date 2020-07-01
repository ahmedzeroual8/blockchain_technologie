import binascii
from collections import OrderedDict

import Crypto
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from flask import Flask, jsonify, request, render_template


class Transaction:
    # definir la structure de la transaction
    def __init__(self, Cle_Public_Emetteur, Cle_Prive_Emetteur, Cle_Public_recepteur, valeur):
        self.Cle_Public_Emetteur = Cle_Public_Emetteur
        self.Cle_Prive_Emetteur = Cle_Prive_Emetteur
        self.Cle_Public_recepteur = Cle_Public_recepteur
        self.valeur = valeur

    def to_dict(self):
        return OrderedDict({'Cle_Public_Emetteur': self.Cle_Public_Emetteur,
                            'Cle_Public_recepteur': self.Cle_Public_recepteur,
                            'valeur': self.valeur})

    def signature_transaction(self):
        cle_prive = RSA.importKey(binascii.unhexlify(self.Cle_Prive_Emetteur))
        signer = PKCS1_v1_5.new(cle_prive)
        h = SHA.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('./aceuille.html')


@app.route('/index')
def indexe():
    return render_template('./index.html')


@app.route('/effectuer/transaction')
def effectuer_transaction():
    return render_template('./effectuer_transaction.html')


@app.route('/consulter/transactions')
def consulter_transaction():
    return render_template('./consulter_transaction.html')


# cette api renvoie les deux cle
@app.route('/nouvelle/wallet', methods=['GET'])
def nouveau_portefeuille():
    cle_aleatoire = Crypto.Random.new().read
    cle_prive = RSA.generate(1024, cle_aleatoire)  # 1024 nombre de bit et RSA pour generer la cle
    cle_public = cle_prive.publickey()
    response = {
        'cle_prive': binascii.hexlify(cle_prive.exportKey(format='DER')).decode('ascii'),
        'cle_public': binascii.hexlify(cle_public.exportKey(format='DER')).decode('ascii')
    }

    return jsonify(response), 200


# cette api permet de remplire les champs a fin d'effectuer une transzaction
@app.route('/generer/transaction', methods=['POST'])
def generer_transaction():
    Cle_Public_Emetteur = request.form['Cle_Public_Emetteur']
    Cle_Prive_Emetteur = request.form['Cle_Prive_Emetteur']
    Cle_Public_recepteur = request.form['Cle_Public_recepteur']
    valeur = request.form['montant']

    transaction = Transaction(Cle_Public_Emetteur, Cle_Prive_Emetteur, Cle_Public_recepteur, valeur)

    response = {'transaction': transaction.to_dict(), 'signature': transaction.signature_transaction()}

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8081, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port, debug=True)
