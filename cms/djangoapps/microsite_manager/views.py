import errno
import os
import re
import logging

from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import View
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from edxmako.shortcuts import render_to_response, render_to_string
from util.json_request import  JsonResponse, JsonResponseBadRequest

from django.views.decorators.csrf import ensure_csrf_cookie

from django.contrib.auth.models import User

from organizations.models import Organization


from django.http import QueryDict

from .microsite_manager import microsite_manager

from django.views.decorators.http import require_GET, require_POST ,require_http_methods

from util.views import require_global_staff
from django.contrib.sites.models import Site
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
log = logging.getLogger(__name__)


@login_required
@ensure_csrf_cookie
@require_POST
@require_global_staff
def create_microsite(request):
    return microsite_manager().create(request)


@login_required
@ensure_csrf_cookie
@require_global_staff
def admin_microsite(request, microsite_id=None):
    if request.method == 'GET':
        #try:
        log.info(microsite_id)
        microsite = SiteConfiguration.objects.get(id=microsite_id)
        log.info(microsite)
        microsite_name = microsite.site_values['platform_name']
        microsite_value = microsite.site_values
        context = {}
        context['key'] = microsite_id
        context['site_id'] = microsite_id
        context['microsite_value'] = microsite_value
        context['microsite_admin'] = microsite_manager().get_microsite_admin_manager(microsite)
        log.info(context['microsite_admin'])
        return render_to_response('admin_microsite.html',context)



def microsite_admin_manager(request, microsite_key):
    microsite = SiteConfiguration.objects.get(id=microsite_key)
    log.info(microsite)
    return microsite_manager().microsite_admin_manager(request, microsite)

@login_required
def update_microsite(request, microsite_id=None):
    if request.method == 'GET':
        return microsite_manager().manage_microsite_data(request, microsite_id)
    elif request.method == 'POST':
        return microsite_manager().update_microsite_data(request, microsite_id)

@login_required
@ensure_csrf_cookie
@require_global_staff
def disclaimer_microsite(request, microsite_key):
    return microsite_manager().microsite_disclaimer_update(request, microsite_key)
