from pymongo import MongoClient
from django.conf import settings
from bson import CodecOptions, SON
import os
from bson.son import SON
import logging

from bson.objectid import ObjectId

class forumMessages():

    def __init__(self,course_id,user_id=None):

        self.course_id = course_id
        self.user_id = user_id
        self.host = settings.MODULESTORE.get("default").get('OPTIONS').get('stores')[0].get('DOC_STORE_CONFIG').get('host')[0]
        self.port = settings.MODULESTORE.get("default").get('OPTIONS').get('stores')[0].get('DOC_STORE_CONFIG').get('port')
        self.client = None
        self.db = None
        self.content_collection = None
        self.user_collection = None
        self.connection()

    def connection(self):

        db = "cs_comments_service_development"
        content_collection = "contents"
        user_collection = "users"

        self.client = MongoClient(self.host, self.port)
        self.db = self.client[db]

        opts = CodecOptions(document_class=SON)

        self.content_collection = self.db[content_collection].with_options(codec_options=opts)
        self.user_collection = self.db[user_collection].with_options(codec_options=opts)

    def get_courses_comments(self,exclude=None):

        if not isinstance(exclude, list):
            exclude = []

        query = {
            "course_id":self.course_id,
            "_type" : "CommentThread",
            "_id": { "$nin": exclude }
        }

        values = self.content_collection.find(query)

        return list(values)

    def get_comments_by_ids(self,_id):

        query = {
            "_id":ObjectId(_id)
        }

        value = self.content_collection.find_one(query)

        return value

    def is_user_oldest_post(self):

        if self.user_id is not None:
            query = {
                "external_id":str(self.user_id)
            }
            value = self.user_collection.find_one(query).get("read_states")
            util_content = []
            for row in value:
                if row.get('course_id') == self.course_id:
                    for keys,values in row.get("last_read_times").items():
                        value = self.get_comments_by_ids(keys)
                        if value is not None:
                            if value.get('updated_at') != value:
                                util_content.append(ObjectId(keys))
            return util_content
        else:

            return None
