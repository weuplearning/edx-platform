# -*- coding: utf-8 -*-

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# mailing
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests  
import smtplib

import logging
log = logging.getLogger()


@csrf_exempt
@require_POST
def contact_msg(request):

    toaddr = 'support@weuplearning.com'
    cc = ['cyril.adolf@weuplearning.com']

    name = str(request.POST.get('name'))
    email = str(request.POST.get('email'))
    message = str(request.POST.get('message'))

    url = str(request.site)

    if name and message and email : 

        html = "<html><head></head><body><p>Bonjour,</br></p> <p>Vous avez re&ccedil;u un message sur le formulaire de contact de la plateforme : " + url + " </a>:</p><p>nom : " + name + "</p> <p>email : " + email + "</p>  <p>message : " + message + "</p> </br>  </body></html>"

        part2 = MIMEText(html, 'html')
        fromaddr = 'WeUp <ne-pas-repondre@themoocagency.com>'
        toaddrs = [toaddr] + cc

        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = 'Formulaire de contact FAQ : ' + url 

        server = smtplib.SMTP('mail3.themoocagency.com', 25)
        server.starttls()
        server.login('contact', 'waSwv6Eqer89')
        msg.attach(part2)
        text = msg.as_string()
        server.sendmail(fromaddr, toaddrs, text)
        server.quit()

        return JsonResponse({'email': email})

    return JsonResponse({'error': 'Champs requis manquants.'}, status=400)
