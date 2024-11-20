from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST,require_GET,require_http_methods

from util.json_request import JsonResponse

from forum_api.api import forumApi

@login_required
@require_GET
def new_message(request,course_id):
    user_id = str(request.user.id)
    return JsonResponse(forumApi(course_id,user_id=user_id).new_post_not_read())
