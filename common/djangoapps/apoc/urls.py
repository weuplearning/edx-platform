from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns(
    'apoc.views',

    url(r'^current_stage/$', 'current_stage', name='info_current_stage'),
    url(r'^status_and_score/$', 'status_and_score', name='follow_status_and_score'),
    url(r'^status_and_score/$', 'status_and_score', name='follow_status_and_score'),
)

