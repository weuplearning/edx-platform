# -*- coding: utf-8 -*-
from .utils import ensure_form_factory
from django.http import HttpResponse
from util.json_request import JsonResponse
from django.conf import settings
from student.models import User,UserProfile
from edxmako.shortcuts import render_to_response
import json
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import requires_csrf_token
from django.contrib.auth.decorators import login_required


@requires_csrf_token
@login_required
@require_http_methods(["GET", "POST"])
def ensure_form(request, user_id=None):
    #elements comments aux call GET ET POST
    form_factory = ensure_form_factory()
    db = 'ensure_form'
    collection = 'certificate_form'
    form_factory.connect(db=db,collection=collection)
    if user_id:
        user = User.objects.get(id=user_id)
    else :
        user = request.user
    form_factory.get_user_form_extra(user)
    form_factory.get_user_certificate_form_extra(user)
    # SI REQ GET, RENVOI ETAT DES FORMULAIRES
    if request.method == 'GET':

        check_form_extra = form_factory.check_form_extra()
        check_certificate_form_extra = form_factory.check_certificate_form_extra()

        context = {
    	    'form_extra': form_factory.user_form_extra,
    	    'certificate_form_extra': form_factory.user_certificate_form_extra,
            'check_form_extra':check_form_extra,
            'check_certificate_form_extra':check_certificate_form_extra,
            'default_form_extra':form_factory.form_extra,
            'default_certificate_form_extra':form_factory.certificate_form_extra,
        }
    # SI REQ POST, AJOUT DE DONNES DANS LE FORMULAIRE
    elif request.method == 'POST':
        form_factory.get_request_values(request, read_from_post = True)
        update_form_extra = form_factory.update_form_extra()
        update_certificate_form_extra = form_factory.update_certificate_form_extra()
        fields = []
        for n in update_form_extra['updates_values']:
            fields.append(n)
        for n in update_certificate_form_extra['updates_values']:
            fields.append(n)
        check_form_extra = form_factory.check_form_extra()
        check_certificate_form_extra = form_factory.check_certificate_form_extra()
        context = {
            'fields': fields,
            'check_form_extra': check_form_extra,
            'check_certificate_form_extra': check_certificate_form_extra
        }

    return JsonResponse(context)

# view page:
@login_required
@require_http_methods(["GET"])
@requires_csrf_token
def ensure_form_views(request):
    user = request.user

    form_factory = ensure_form_factory()
    db = 'ensure_form'
    collection = 'certificate_form'
    form_factory.connect(db=db,collection=collection)
    user = request.user
    form_factory.get_user_form_extra(user)
    form_factory.get_user_certificate_form_extra(user)
    context = form_factory.form_render(request)

    return render_to_response('ensure_form.html', context)
