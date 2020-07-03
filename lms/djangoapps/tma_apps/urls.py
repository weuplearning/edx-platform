from django.conf.urls import url
from django.conf import settings
from .completion import views as completion_views


urlpatterns = [
    #Completion
    url(r'^{}/completion/get_course_completion$'.format(settings.COURSE_ID_PATTERN), completion_views.get_course_completion),
    url(r'^{course_id}/{unit_id}/completion/get_unit_completion$'.format(course_id=settings.COURSE_ID_PATTERN, unit_id=settings.USAGE_KEY_PATTERN), completion_views.get_unit_completion)
]
