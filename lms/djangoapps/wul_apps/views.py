from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
import os


import logging
log = logging.getLogger(__name__)


def media_access(request, path):
    user = request.user
    log.info("inside media access")
    if user.is_authenticated():
        log.info("user is authenticated")
        response = HttpResponse()
        # Content-type will be detected by nginx
        del response['Content-Type']
        response['X-Accel-Redirect'] = '/protected/media/' + path
        log.info(f"response: {response}")
        return response
    else:
        return HttpResponseForbidden('Not authorized to access this media.')




@login_required
def protected_media_view(request, filename):
    # Construct the full path to the media file
    media_path = os.path.join(settings.MEDIA_ROOT, filename)
    log.info('in protected_media_view')

    # Check if the file exists and return it as an HttpResponse
    if os.path.exists(media_path):
        with open(media_path, 'rb') as media_file:
            response = HttpResponse(media_file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(media_path)}"'
            return response
    else:
        # Handle the case when the file does not exist
        return HttpResponse(status=404)
