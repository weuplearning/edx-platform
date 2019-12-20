"""
URLs for bulk_email app
"""

from django.conf.urls import url

from bulk_email import views

urlpatterns = [
    url(
        r'^email/optout/(?P<token>[a-zA-Z0-9-_=]+)/',
        views.opt_out_email_updates,
        name='bulk_email_opt_out',
    ),
]
