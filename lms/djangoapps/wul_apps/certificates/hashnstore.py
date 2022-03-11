#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import os
import hashlib
import ed25519

import logging
log = logging.getLogger()

class HashnStoreManager():
    def __init__(self):
        self.token_url="https://validity.eu.auth0.com/oauth/token"
        self.submit_url="https://hashnstore-validity.herokuapp.com/v1/entries"
        self.username="tma"
        self.password="TheMooc@gency"
        self.client_secret="cZpCX36B7VIZasN8-4m5NOHocQy9Dx6P1fXLlRCoCFmWFmiEgy4IGw9C6PutdCfU";
        self.client_id="aLwCXY3cs6xZpnCeGxmcuU41Sp6Pb8PE";

    def get_access_token(self):
        headers={
            "content_type":"application/json"
        }
        data={
          "grant_type":"password",
          "username": self.username,
          "password": self.password,
          "audience":"https://validity.fr/api",
          "client_id":self.client_id,
          "client_secret":self.client_secret}
        response = requests.post(self.token_url, json=data, headers=headers)
        return json.loads(response._content).get('access_token')

    def get_signing_key(self):
        #signing_key, verifying_key = ed25519.create_keypair()
        #open("/edx/app/edxapp/edx-platform/lms/djangoapps/tma_apps/certificates/hashnstore_sk.txt","wb").write(signing_key.to_bytes())
        keydata = open("/edx/app/edxapp/edx-platform/lms/djangoapps/tma_apps/certificates/hashnstore_sk.txt","rb").read()
        signing_key = ed25519.SigningKey(keydata)
        return signing_key

    def make_hashnstore_registration(self, file_content, filename):
        hash=hashlib.sha512(file_content).hexdigest()
        hashd=hashlib.sha512(hash).hexdigest()

        #WORKING => USING PROVIDED KEY
        signing_key_64="c6zgV9yL8yQgDALrN38i8ynfLhNTPky9UIRJdvYq07Dx6xU5p7fOUqpj1ieVgUiEDud3+9Dq1nFRUjpJw5xoZQ=="
        verifying_key_64="8esVOae3zlKqY9YnlYFIhA7nd/vQ6tZxUVI6ScOcaGU="
        signing_key=ed25519.SigningKey(signing_key_64, encoding="base64")
        verifying_key=ed25519.VerifyingKey(verifying_key_64, encoding="base64")
        vkey_hex = verifying_key.to_ascii(encoding="hex")
        witness_signature = signing_key.sign(hashd, encoding="hex")
        signee_signature = signing_key.sign(witness_signature, encoding="hex")

        access_token=self.get_access_token()

        submit_headers={
            "Content-Type":"application/json",
            "Authorization":"Bearer "+access_token,
        }

        submit_body={
            "data":[
            {
                "hash":hash,
                "witness_signature":witness_signature,
                "signee_signature":signee_signature,
                "witness_key":{
                    "public_key":vkey_hex,
                    "encoding": "hex",
                    "signature_algo": "ed25519"
                },
                "signee_key":{
                    "public_key":vkey_hex,
                    "encoding": "hex",
                    "signature_algo": "ed25519"
                },
                "chainid_name":"TMA",
                "file_name":filename,
                "visible":1
            }
            ]
        }
        log.info("submit_body {}".format(submit_body))
        response = requests.post(self.submit_url, data=json.dumps(submit_body), headers=submit_headers)
        log.info("response")
        log.info(response.content)
