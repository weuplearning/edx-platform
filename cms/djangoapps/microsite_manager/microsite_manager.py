# -*- coding: utf-8 -*-

import errno
import os
import re
import logging
import json
import requests

from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict
from django.views.generic import View
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.conf import settings
from edxmako.shortcuts import render_to_response, render_to_string
from util.json_request import  JsonResponse, JsonResponseBadRequest
from util.views import require_global_staff

from django.contrib.auth.models import User

from organizations.models import Organization
import unicodedata
from distutils.dir_util import copy_tree
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from openedx.core.djangoapps.site_configuration.admin import SiteConfigurationAdmin




log = logging.getLogger(__name__)



class microsite_manager():
    def __init__(self):
        self.logo = None
        self.logo_couleur = None
        self.microsite_name = None
        self.primary_color = None
        self.secondary_color = None
        self.third_color = None
        self.third_text_color = None
        self.white_or_color_logo = None
        self.language = None
        self.contact_address = None
        self.amundi_brand = None
        self.disclaimer=None
        self.trademark=None
        self.admin=None
        self.platform_name=None
        self.course_org_filter=None


    #CHECK ALL ELEMENTS AND CREATE MICROSITE
    def remove_accents(self, input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def create(self,request):
        logo_couleur_ext = request.FILES.get('logo_couleur').name.split('.')[1]
        log.info(u'microsite_manager.create start')
        context = {
            "mode":"create",
            "status":False
        }
        require_keys = [
            'display_name','logo','primary_color',

            'secondary_color','third_color','third_text_color','white_or_color_logo','language',
            'logo_couleur', 'contact_address', 'amundi_brand'
        ]
        if request.method == 'POST':
            #CHECK ALL REQUIRED ELEMENTS ARE SENT BY POST
            _ensure = True
            for key,value in request.POST.items():
                log.info(u'microsite_manager.create key:{},value:{}'.format(str(key),str(value)))
                if not key in require_keys or not value:
                    _ensure = False
            for key,value in request.FILES.items():
                log.info(u'microsite_manager.create key:{},value:{}'.format(str(key),str(value)))
                if not key in require_keys or not value:
                    _ensure = False

            #IF REQUEST POST IS OK
            if _ensure:
                log.info(u'microsite_manager.create _ensure')
                log.info(u'request.POST : {}'.format(str(request.POST.__dict__)))
                log.info(u'request.FILES : {}'.format(str(request.FILES.__dict__)))
                #add request values to class attributes
                self.add(
                    microsite_name=request.POST.get('display_name'),
                    platform_name=request.POST.get('display_name'),
                    course_org_filter=request.POST.get('display_name'),
                    logo=request.FILES.get('logo'),
                    logo_couleur=request.FILES.get('logo_couleur'),
                    primary_color=request.POST.get('primary_color'),
                    secondary_color=request.POST.get('secondary_color'),
                    third_color=request.POST.get('third_color'),
                    third_text_color=request.POST.get('third_text_color'),
                    white_or_color_logo=request.POST.get('white_or_color_logo'),
                    language = request.POST.get('language'),
                    contact_address = request.POST.get('contact_address'),
                    amundi_brand = request.POST.get('amundi_brand'),
                    disclaimer=request.POST.get('disclaimer'),
                    trademark=request.POST.get('trademark'),
                    admin=request.POST.get('admin')
                )

                #microsite values to sql db
                # Set the mother domain name
                mother_domain = settings.LMS_BASE

                #set cookie domain
                cookie_domain = '.' + mother_domain

                # Create site
                site_name = self.microsite_name + '.' + mother_domain
                log.info(u'microsite_manager.create site')
                site, created = Site.objects.get_or_create(
                    domain=site_name,
                    name=self.microsite_name.capitalize()
                )
                # Create microsite using Database backend
                log.info(u'microsite_manager.create microsite')
                microsite = SiteConfiguration.objects.create(
                    site=site,

                    site_values = {
                     "domain_prefix":self.microsite_name,
                     "university":self.microsite_name,
                     "platform_name":self.microsite_name,
                     "course_org_filter":self.microsite_name,
                     "logo":"/media/microsite/"+self.microsite_name+"/images/"+self.logo.name,
                     "logo_couleur":"/media/microsite/"+self.microsite_name+"/images/"+self.logo_couleur.name,
                     "SITE_NAME":site_name,
                     "course_org_filter":self.microsite_name,
                     "primary_color":self.primary_color,
                     "secondary_color":self.secondary_color,
                     "third_color":self.third_color,
                     "third_text_color":self.third_text_color,
                     "white_or_color_logo":self.white_or_color_logo,
                     "ENABLE_THIRD_PARTY_AUTH":True,
                     "ALWAYS_REDIRECT_HOMEPAGE_TO_DASHBOARD_FOR_AUTHENTICATED_USER":True,
                     "course_email_from_addr":"ne-pas-repondre@themoocagency.com",
                     "SESSION_COOKIE_DOMAIN":cookie_domain,
                     "language_code":self.language,
                     "contact_address":self.contact_address,
                     "amundi_brand":self.amundi_brand,
                     "disclaimer":self.disclaimer,
                     "trademark":self.trademark,
                     "admin":self.admin,
                     },
                     enabled=True
                )


                #add static values
                log.info(u'microsite_manager.create add_static_values')
                _static = self.add_static_values()
                context["status"] = _static
                context["url"] = '/home'
                microsite.site_values["site_id"] = microsite.pk
                microsite.save()

        return JsonResponse(context)

    #CHECK FORMAT ADD MICROSITE ATTRIBUTES (colors etc...) to self attributes
    def add(self,microsite_name=None,logo=None,logo_couleur=None,bg_img=None,primary_color=None,secondary_color=None,third_color=None,third_text_color=None,white_or_color_logo=None,language=None,contact_address=None, amundi_brand=None, disclaimer=None, trademark=None,admin=[],course_org_filter=None,platform_name=None):
        log.info(u'microsite_manager.add start')

        valid_ext = ['jpg','jpeg','png']
        valid_ico = ['jpg','jpeg','png','ico']

        #erase all accents and spaces in file names
        if logo is not None:
            logo.name=self.remove_accents(logo.name)
            logo.name=logo.name.replace(' ', '_')
        if logo_couleur is not None:
            logo_couleur.name=self.remove_accents(logo_couleur.name)
            logo_couleur.name=logo_couleur.name.replace(' ', '_')

        #ensure logo formatis valid
        if logo is not None:
            l_ext = logo.name.split('.')[1]
            log.info(u'microsite_manager.add logo name : {}'.format(str(logo.name)))
            if l_ext.lower() in valid_ext:
                log.info(u'microsite_manager.add logo ext : {}'.format(str(l_ext)))
                logo.name = "logo.{}".format(l_ext)
                self.logo = logo
        #ensure logo_couleur is valid
        if logo_couleur is not None:
            lcouleur_ext = logo_couleur.name.split('.')[1]
            log.info(u'microsite_manager.add logo_couleur name : {}'.format(str(logo_couleur.name)))
            if lcouleur_ext.lower() in valid_ext:
                log.info(u'microsite_manager.add logo_couleur ext : {}'.format(str(lcouleur_ext)))
                logo_couleur.name = "logo_couleur.{}".format(lcouleur_ext)
                self.logo_couleur = logo_couleur

        if microsite_name !='':
            self.microsite_name = microsite_name
        if language !='':
            self.language = language
        if primary_color!='':
            self.primary_color = primary_color
        if secondary_color!='':
            self.secondary_color = secondary_color
        if third_color!='':
            self.third_color = third_color
        if third_text_color!='':
            self.third_text_color = third_text_color
        if white_or_color_logo!='':
            self.white_or_color_logo = white_or_color_logo
        if contact_address!='':
            self.contact_address=contact_address
        if amundi_brand!='':
            if amundi_brand=="false" :
                self.amundi_brand=False
            if amundi_brand =="true":
                self.amundi_brand=True
        if trademark!='':
            self.trademark=trademark
        else :
            self.trademark=''
        if admin!='':
            self.admin=admin
        else :
            self.admin=''
        if disclaimer!='' and disclaimer is not None:
            self.disclaimer=disclaimer
        else :
            self.disclaimer=''

    #DISPLAY MICROSITE DATA AND MANAGE IT
    def manage_microsite_data(self, request, microsite_id=None):
        site_config = SiteConfiguration.objects.get(id=microsite_id)
        microsite_value = site_config.site_values


        lang_key = 0
        logo_key = 0
        primary_key = 0
        secondary_key = 0
        third_key = 0
        third_bg_key = 0
        white_or_color_logo_key = 0
        white_or_color_logo_key = 0
        i = 0

        context = {}
        try:
            context['course_org_filter'] = microsite_value['course_org_filter']
        except:
            context['course_org_filter'] = "Amundi"
        try:
            context['platform_name'] = microsite_value['platform_name']
        except:
            context['platform_name'] = "Amundi"
        try:
            context['course_org_filter'] = microsite_value['course_org_filter']
        except:
            context['course_org_filter'] = "Amundi"
        try:
            context['key'] = microsite_value['course_org_filter']
        except:
            context['key'] = 'Amundi'
        try:
            context['primary_color'] = microsite_value['primary_color']
        except:
            context['primary_color'] = '#000000'
        try:
            context['secondary_color'] = microsite_value['secondary_color']
        except:
            context['secondary_color'] = '#ffffff'
        try :
            context['third_color'] = microsite_value['third_color']
        except:
            context['third_color'] = '#000000'
        try :
            context['third_text_color'] = microsite_value['third_text_color']
        except:
            context['third_text_color'] = '#ffffff'
        try :
            context['white_or_color_logo'] = microsite_value['white_or_color_logo']
        except:
            context['white_or_color_logo'] = ''
        try :
            context['logo_site'] = microsite_value['logo_site']
        except:
            context['logo_site'] = ''
        try:
            context['logo_couleur'] = microsite_value['logo_couleur']
        except:
            context['logo_couleur'] ='';
        try:
            context['amundi_brand'] = microsite_value['amundi_brand']
        except:
            context['amundi_brand'] ='';
        try:
            context['contact_address'] = microsite_value['contact_address']
        except:
            context['contact_address'] ='';
        try:
            context['disclaimer'] = microsite_value['disclaimer']
        except:
            context['disclaimer'] ='';
        try:
            context['trademark'] = microsite_value['trademark']
        except:
            context['trademark'] ='';
        try:
            context['admin'] = microsite_value['admin']
        except:
            context['admin'] =[];
        context['microsite_value'] = microsite_value

        return render_to_response('update-microsite.html',context)

    #UPDATE MICROSITE DATA
    def update_microsite_data(self,request, microsite_id=None):
        if request.method == 'POST':
            log.info(u'microsite_manager.update_static microsite_id : {} user_email = {}'.format(str(microsite_id),str(request.user.email)))

            user_email = request.user.email

            #GET CURRENT SITE INFORMATONS
            _cur_microsite = SiteConfiguration.objects.get(id=microsite_id)
            #UPDATE CLASS PROPERTIES WITH NEW VALUES IF ANY

            log.info(request.POST)
            log.info(str(request.POST.get('key')))
            self.add(
                logo=request.FILES.get('logo'),
                logo_couleur=request.FILES.get('logo_couleur'),
                primary_color=str(request.POST.get('primary_color')),
                secondary_color=str(request.POST.get('secondary_color')),
                third_color=str(request.POST.get('third_color')),
                third_text_color=str(request.POST.get('third_text_color')),
                white_or_color_logo=str(request.POST.get('white_or_color_logo')),
                language = str(request.POST.get('language')),
                contact_address = str(request.POST.get('contact_address')),
                amundi_brand = str(request.POST.get('amundi_brand')),
                disclaimer=str(request.POST.get('disclaimer')),
                trademark=str(request.POST.get('trademark')),
                admin=str(request.POST.get('admin')),
                course_org_filter=str(request.POST.get('key')),
                platform_name=str(request.POST.get('key'))
            )

            #SAVE NEW STATIC FILES (IMAGES LOGO)
            _static = self.add_static_values(_cur_microsite)
            log.info(u'microsite_manager.update_static _static : {}'.format(str(_static)))

            #UPDATE MICROSITE OBJECT WITH NEW INFO
            values = _cur_microsite
            q = {}
            i = 0
            for n in values.site_values:
                q[n] =  values.site_values[n]
                log.info(values.site_values[n])
                log.info(q[n])
                i = i + 1
            log.info(q)
            for key,value in _static.items():

                q[key] = value
            log.info(_cur_microsite.site_values)
            log.info(q)
            _cur_microsite.site_values = q
            _cur_microsite.save()
            return JsonResponse(_static)

    #SAVE IMAGES (logo etc...) / COPY TEMPLATE FILES / ADAPT CSS FILES
    def add_static_values(self, _cur_microsite=None):
        if self.microsite_name is None:
            microsite_name = _cur_microsite.site_values['course_org_filter']
            microsite_name = _cur_microsite.site_values['platform_name']
        else :
            microsite_name = self.microsite_name

        #where microsite files will be stored
        static_path = "/edx/var/edxapp/media/microsite/{}/".format(microsite_name.lower())
        image_path = static_path+'images/'
        css_path = static_path+'css'

        #SAVE LOGO IMG
        if self.logo is not None:
            logo_path = image_path+self.logo.name
            try:
                os.makedirs(os.path.dirname(logo_path))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
            try:
                with open(logo_path, 'wb+') as destination:
                    for chunk in self.logo.chunks():
                        destination.write(chunk)
            except:
                pass

        #SAVE LOGO_COULEUR IMG
        if self.logo_couleur is not None:
            logo_couleur_path = image_path+self.logo_couleur.name
            try:
                os.makedirs(os.path.dirname(logo_couleur_path))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
            try:
                with open(logo_couleur_path, 'wb+') as destination:
                    for chunk in self.logo_couleur.chunks():
                        destination.write(chunk)
            except:
                pass




        #Replace missing values for colors replacement and final context
        if _cur_microsite is not None:
            microsite_value = _cur_microsite
            if self.primary_color is None :
                self.primary_color = microsite_value.site_values['primary_color']
            if self.secondary_color is None :
                self.secondary_color = microsite_value.site_values['secondary_color']
            if self.third_color is None :
                self.third_color = microsite_value.site_values['third_color']
            if self.third_text_color is None :
                self.third_text_color = microsite_value.site_values['third_text_color']
            if self.white_or_color_logo is None :
                self.white_or_color_logo = microsite_value.site_values['white_or_color_logo']
            if self.language is None :
                self.language = microsite_value.site_values['language_code']
            if self.contact_address is None :
                self.contact_address = microsite_value.site_values['contact_address']
            if self.amundi_brand is None :
                self.amundi_brand = microsite_value.site_values['amundi_brand']
            if self.disclaimer is None :
                self.disclaimer = microsite_value.site_values['disclaimer']
            if self.trademark is None :
                self.trademark = microsite_value.site_values['trademark']
            if self.admin is None :
                self.admin = microsite_value.site_values['admin']
            if self.platform_name is None :
                self.platform_name = microsite_value.site_values['platform_name']
            if self.course_org_filter is None :
                self.course_org_filter = microsite_value.site_values['course_org_filter']

        #REPLACE COLORS IN CSS FILES
        if self.primary_color is not None and self.secondary_color is not None and self.third_color is not None and self.third_text_color is not None:
            dict_change = {
                '!atp_primary_color': self.primary_color,
                '!atp_secondary_color': self.secondary_color,
                '!atp_third_color': self.third_color,
                '!atp_third_text_color': self.third_text_color,
                '!font_family_atp': 'mywebfont'
            }

            #create media/microsite/self.microsite/css folder
            if not os.path.exists(css_path):
                os.makedirs(css_path)

            context = {
                'primary_color':str(self.primary_color),
                'secondary_color':str(self.secondary_color),
                'third_color':str(self.third_color),
                'third_text_color':str(self.third_text_color),
                'white_or_color_logo':str(self.white_or_color_logo),
                'contact_address':str(self.contact_address),
                'amundi_brand':str(self.amundi_brand),
                'disclaimer':str(self.disclaimer),
                'trademark':str(self.trademark),
                'admin':str(self.admin),
                'platform_name':str(self.platform_name),
                'course_org_filter':str(self.course_org_filter)
            }
            if self.logo is not None:
                context['logo']=format(logo_path.replace("/edx/var/edxapp",""))
            else:
                context['logo']=microsite_value.site_values['logo']
            if self.logo_couleur is not None:
                context['logo_couleur']=format(logo_couleur_path.replace("/edx/var/edxapp",""))
            else:
                context['logo_couleur']=microsite_value.site_values['logo_couleur']
            return context
        else:
            return True



    def get_microsite_admin_manager(self, microsite):
        context = {}

        try:
            log.info(microsite)
            log.info( SiteConfiguration.objects.get(id=microsite.id).site_values)
            microsite_manager = SiteConfiguration.objects.get(id=microsite.id).site_values['admin']
            users = []
            for n in microsite_manager:
                try:
                    log.info(n)
                    user = User.objects.get(id=n)
                    email = user.email
                    q = {}
                    q['user_id'] = int(n)
                    q['email'] = email
                    users.append(q)
                except:
                    log.info('except user')
                    test = None
            context['users_admin'] = users
            context['status'] = True

        except:
            context['status'] = False

        return context

    #
    def microsite_admin_manager(self, request, microsite):
        #get request methods
        methods = request.method
        #if REQUEST GET
        context = {}
        if methods == 'POST':
            email = request.POST['data']
            check_user = True
            check_microsite = True
            user = None
            try:
                user = User.objects.get(email=email)
                log.info(user)
            except:
                check_user = False
                context['user'] = 'email invalide'
            try:
                log.info(microsite)
            except:
                log.info(SiteConfiguration.objects.get(id=microsite.id))
                check_microsite = False
                context['microsite'] = 'microsite invalide'

            if check_user and check_microsite:
                log.info('checked')

                check_microsite = True
                try:
                    log.info('add')
                    user.id in SiteConfiguration.objects.get(id=microsite.id).site_values['admin']
                    context['microsite_admin'] = False
                except:
                    log.info('don t work')
                    check_microsite = False

                if not user.id in SiteConfiguration.objects.get(id=microsite.id).site_values['admin']:
                    #try:
                    microsite_admin_manager = SiteConfiguration.objects.get(id=microsite.id)
                    microsite_admin_manager_value = microsite_admin_manager.site_values['admin']
                    microsite_admin_manager_value.append(user.id)
                    microsite_admin_manager.save()
                    context['microsite_admin'] = True
                    context['user_id'] = user.id
                    context['user_email'] = user.email
                    """
                    except:
                        context['microsite_admin'] = False
                    """

        if methods == 'DELETE':
            request.META['REQUEST_METHOD'] = 'DELETE'
            request.DELETE = QueryDict(request.body)
            user_id = request.DELETE['data']
            check_user = True
            check_microsite = True
            user = None
            context['user_id'] = user_id
            log.info('DELETE')
            try:
                user = User.objects.get(pk=user_id)
            except:
                check_user = False
                context['user'] = 'user invalide'
            try:
                log.info(SiteConfiguration.objects.get(id=microsite.id))
                log.info(microsite)
            except:
                log.info(SiteConfiguration.objects.get(id=microsite.id))
                check_microsite = False
                context['microsite'] = 'microsite invalide'

            if check_user and check_microsite and user.id in SiteConfiguration.objects.get(id=microsite.id).site_values['admin']:
                log.info('deleting')
                check_microsite = True
                try:
                    microsite_admin_manager = SiteConfiguration.objects.get(id=microsite.id)
                    microsite_admin_manager_value = microsite_admin_manager.site_values['admin']
                    microsite_admin_manager_value.remove(user.id)
                    microsite_admin_manager.save()
                    context['delete'] = True
                except:
                    context['delete'] = False
        context['methods'] = methods
        return JsonResponse({'context':context})
