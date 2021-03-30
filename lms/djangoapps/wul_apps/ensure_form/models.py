# -*- coding: utf-8 -*-
from pymongo import MongoClient
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

class ensure_form_models():
    def __init__(self):
        #user_id
        self.user_id = int
        #microsite name
        self.microsite = configuration_helpers.get_value('domain_prefix')
        #MONGO HOST
        self.host = settings.MODULESTORE.get("default").get('OPTIONS').get('stores')[0].get('DOC_STORE_CONFIG').get('host')[0]
        #MONGO PORT
        self.port = settings.MODULESTORE.get("default").get('OPTIONS').get('stores')[0].get('DOC_STORE_CONFIG').get('port')
        #mongo client
        self.client = None
        #mongo db
        self.db = None
        #mongo collection
        self.collection = None

    # methode connection à la db mongo
    def connect(self,db=None,collection=None):

        try:
            self.client = MongoClient(self.host, self.port)
        except:
            self.client = MongoClient()

        if db is not None:
            self.db = self.client[db]
            if collection is not None:
                self.collection = self.db[collection]

    #methode de recuperation par user_id ou microsite voirs les deux
    def getForm(self,user_id=False,microsite=False):
        q = {}
        if microsite:
            q['microsite'] = self.microsite
        if user_id:
            q['user_id'] = self.user_id

        search = self.collection.find_one(q)

        return search

    # methode insert en bdd // update
    def insert_row(self,_dict):

        check = self.getForm(user_id=True,microsite=True)
        q = {}
        if check is None:
            q['microsite'] = self.microsite
            q['user_id'] = self.user_id
            q['form'] = _dict
            self.collection.insert(q)
            return q
        else:
            for key,value in _dict.items():
                if not key in check['form'].keys():
                    check['form'][key] = value
                else:
                    if check['form'][key] != value:
                        check['form'][key] = value
            self.collection.save(check)
            return check['form']

    #methode update bdd form_extra
    def update_row(self,_dict):
        _get = self.getForm(user_id=True,microsite=True)
        if check is not None:
            for key,value in _dict.items():
                if (_get.get('form')[key] != value) and (value is not None) and value:
                    _get.get('form')[key] = value

            self.collection.save(_get)

