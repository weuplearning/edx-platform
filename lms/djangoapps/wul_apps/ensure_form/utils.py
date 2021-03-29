# -*- coding: utf-8 -*-
import json
from student.models import User,UserProfile
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from .models import ensure_form_models
import logging
log = logging.getLogger()

class ensure_form_factory(ensure_form_models):
    """
    Previously located in 
    lms.djangoapps.tma_ensure_form
    """

    def __init__(self):
        # init parent class attributes
        ensure_form_models.__init__(self)

        self.form_extra = configuration_helpers.get_value('FORM_EXTRA')
        self.certificate_form_extra = configuration_helpers.get_value('CERTIFICATE_FORM_EXTRA')
        if self.certificate_form_extra is None:
            self.certificate_form_extra = []
        self.user_form_extra = None
        self.UserProfile = None
        self.user_certificate_form_extra = None
        self.body_request = None

    #methode de recuperation du form extra de l'utilisateur
    def get_user_form_extra(self,user):
        self.UserProfile = UserProfile.objects.get(user=user)
        custom_fields = self.UserProfile.custom_field
        try:
            custom_fields = json.loads(custom_fields)
        except:
            custom_fields = {}

        for key,value in custom_fields.items():
            if value is None:
                custom_fields[key] = ''

        self.UserProfile.custom_field = json.dumps(custom_fields)
        self.UserProfile.save()
        
        self.user_form_extra = custom_fields

    #methode de recuperation du form extra certificate de l'utilisateur
    def get_user_certificate_form_extra(self,user):
        self.user_id = user.id
        _get = self.getForm(user_id=True,microsite=True)
        _form = {}
        if _get is not None:
            _form = _get.get('form')
        self.user_certificate_form_extra = _form

    #methode recuperation données de requete
    def get_request_values(self,request, read_from_post = False):
        if not read_from_post:
            self.body_request = json.loads(request.body)
        else:
            if str(type(request.POST)) == "<class 'django.http.request.QueryDict'>":
                app_json = json.dumps(request.POST.dict())
                app_json = json.loads(app_json)
                self.body_request = app_json
            else:
                self.body_request = request.POST

    #methode qui verifie que l'utilisateur à bien toutes les données du form_extra en bdd
    def check_form_extra(self):

        context = {
            'miss_fields': [],
            'status': True,
            'required': [],
            'optional': []
        }

        for field in self.form_extra:
            name = field.get('name')
            value = self.user_form_extra.get(name)
            required = field.get('required')
            if not value or value is None:
                context['status'] = False
                context['miss_fields'].append(name)
                if required:
                    context['required'].append(name)
                else:
                    context['optional'].append(name)
        return context

    #methode qui verifie que l'utilisateur à bien toutes les données du certificate_form_extra en bdd
    def check_certificate_form_extra(self):
        context = {
            'miss_fields': [],
            'status': True,
            'required': [],
            'optional': []
        }
        for field in self.certificate_form_extra:
            name = field.get('name')
            value = self.user_certificate_form_extra.get(name)
            required = field.get('required')
            if not value or value is None:
                context['status'] = False
                context['miss_fields'].append(name)
                if required:
                    context['required'].append(name)
                else:
                    context['optional'].append(name)
        return context
    #methode preparation formulaire form_extra
    def update_form_extra(self):

        microsite_form = self.form_extra
        user_form = self.user_form_extra

        change_row = []

        for key,value in self.body_request.items():
            for field in microsite_form:
                name = field.get('name')
                if key == name:
                    if value:
                        user_form[key] = value
                        change_row.append({key:value})


        self.UserProfile.custom_field = json.dumps(user_form)
        self.UserProfile.save()

        context = {
            'updates_values' : change_row,
        }

        return context


    #methode preparation formulaire certificate_form_extra
    def update_certificate_form_extra(self):
        microsite_certificate_form = self.certificate_form_extra
        user_certificate_form_extra = self.user_certificate_form_extra

        change_row = []

        for key,value in self.body_request.items():
            for field in microsite_certificate_form:
                name = field.get('name')
                if key == name:
                    if value:
                        if not name in user_certificate_form_extra.keys():
                            user_certificate_form_extra[key] = value
                            change_row.append({key:value})
                        else:
                            if user_certificate_form_extra[key] != value:
                                user_certificate_form_extra[key] = value
                                change_row.append({key:value})

        insert = self.insert_row(user_certificate_form_extra)

        context = {
            'updates_values':change_row,
        }
        return context

    #methode rendu formulaire
    def form_render(self,request):
        fields = []
        user_fields = {}
        for n in self.form_extra:
            fields.append(n)
            name = n.get('name')
            if not name in self.user_form_extra.keys():
                user_fields[name] = ''
            else:
                user_fields[name] = self.user_form_extra[name]
        for n in self.certificate_form_extra:
            fields.append(n)
            name = n.get('name')
            if not name in self.user_certificate_form_extra.keys():
                user_fields[name] = ''
            else:
                user_fields[name] = self.user_certificate_form_extra[name]

        context = {
            'fields':fields,
            'user_fields':user_fields,
            'request':request
        }
        return context
