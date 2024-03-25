# -*- coding: utf-8 -*-
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
import logging
log = logging.getLogger()

import urllib.request as urllib2
import xmltodict

def is_job_blacklisted(job,blacklist=[]):
    for word in blacklist:
          if job['locales']['locale']['title'].find(word) != -1:
              return True
    return False     

def parse_jobs_dict(input_dict,tag=None,blacklist=[]):
    """ returns dictionnary into parsed list """

    jobs = input_dict['jobs']['job']
    output = []

    for index,job in enumerate(jobs):
        
        # filter offers with blacklist elements in name
        if is_job_blacklisted(job,blacklist):
            break
        
        # description, title , url, reference, region ( format "hdf" "grand-est")
        job_details = job['locales']['locale']
        job_location = job_details['locations']['location']['field']
        
        new_job = dict()
       
        new_job["tag"] = tag if tag else "unknown"
        
        # useful during debug / analysis
        #new_job["originJob"] = job
        #new_job["location"] = job_location
        
        new_job["id"] = job['@id']
        new_job["reference"] = job['reference']
        
        new_job["title"] = job_details['title']
        new_job["jobUrl"] = job_details['jobUrl']
        new_job["applyUrl"] = job_details['url']
        
        job_fields_lookup = [
            { "index" : "43", "value" : "region" },
            { "index" : "67", "value" : "description" },
            { "index" : "45", "value" : "city" },
        ]      

        for field in job_location:
            identifier = field['@id']
            value = field['value']['value']
             
            for lookup in job_fields_lookup:
                if identifier  == lookup["index"]:
                    new_job[lookup["value"]] = value 
                
        output.append(new_job)
    
    return output


def fetch(url):
    """ returns api results in json payload converted from xml"""
    offers_xml_stream = urllib2.urlopen(url)
    offers_xml_data = offers_xml_stream.read()
    offers_xml_stream.close()
    offers_data = xmltodict.parse(offers_xml_data)
    return offers_data


def jobs_url_builder(domain,key_prefix,key,arguments=[]):
    url = domain + key_prefix + key
    for arg in arguments:
        print("ARG")
        url += arg
    return url




@require_http_methods(["GET"])
def get_sncf_jobs_dev(request):
    domain = 'https://preprod.altays-progiciels.com/diffuseur/api/offre/export'
    k = 'vLwSDQP1JK00B6XcB7A75Pyg5ITvWjfJJx3hElJgCAs8YnSFArMWEzRaja9mS2Q2'
    k_prefix = '?ClicNJob_Api_Key='

    # keep only french(lang) jobs
    arguments = ['&noLangue=1']
    
    url = jobs_url_builder(domain=domain,key=k,key_prefix=k_prefix,arguments=arguments)

    jobs = fetch(url)
    jobs = parse_jobs_dict(jobs,tag="dev")
    response = json.dumps(jobs)
    
    return JsonResponse(response, safe=False)



@require_http_methods(["GET"])
def get_sncf_jobs_conduite(request):
    domain = "https://www.altays-progiciels.com/sncf-recrutement-externe/api/offre/export"
    k_conduite_cadres =  "x6xsIMz9oiobKFltPSRUpmwmqnhzjYij317JiCMLXJniqq0trvCGaNTrPJXDzHRG"
    k_conduite_transverse = "XfvdjK61a7oZqRzZgyq9p7HbUgjuwHy3FqL5RPu7l68ZsXLL4AGF9aepd9jBqBpm"
    
    k_prefix = '?ClicNJob_Api_Key='

    blacklist=["FRET"]
    arguments = ['&noLangue=1']
    
    url_conduite_cadres = jobs_url_builder(domain=domain,key=k_conduite_cadres,key_prefix=k_prefix,arguments=arguments)
    url_conduite_transverse = jobs_url_builder(domain=domain,key=k_conduite_transverse,key_prefix=k_prefix,arguments=arguments)


    jobs_cadres = fetch(url_conduite_cadres)
    jobs_cadres = parse_jobs_dict(jobs_cadres,blacklist=blacklist,tag="conduite-cadres")
    
    jobs_transverse = fetch(url_conduite_transverse)
    jobs_transverse = parse_jobs_dict(jobs_transverse,blacklist=blacklist,tag="conduite-transverse")
    
    jobs = jobs_cadres + jobs_transverse
    response = json.dumps(jobs)
    
    return JsonResponse(response, safe=False)


@require_http_methods(["GET"])
def get_sncf_jobs_surete(request):
    domain = "https://www.altays-progiciels.com/sncf-recrutement-externe/api/offre/export"
    k_surete_cadres =  "nQTZzzVwnwnfglpueyWRQ1oEpSVhgSKZDGB5MjR45X4Q4L92j7A8a639YHI4aEXz"
    k_surete_transverse = "01p9ttpfV5XJRGuQ09tysD44g1KGjsjTPrJ37x6kg6SyXHSIJ0x1UDzVAqaU95Zu"
    
    k_prefix = '?ClicNJob_Api_Key='

    # SURETE : No lang argument available (causes 403)
    arguments = ['']
    
    url_surete_cadres = jobs_url_builder(domain=domain,key=k_surete_cadres,key_prefix=k_prefix,arguments=arguments)
    url_surete_transverse = jobs_url_builder(domain=domain,key=k_surete_transverse,key_prefix=k_prefix,arguments=arguments)


    jobs_cadres = fetch(url_surete_cadres)
    jobs_cadres = parse_jobs_dict(jobs_cadres,tag="surete-cadres")
    
    jobs_transverse = fetch(url_surete_transverse)
    jobs_transverse = parse_jobs_dict(jobs_transverse,tag="surete-transverse")
    
    jobs = jobs_cadres + jobs_transverse
    response = json.dumps(jobs)
    
    return JsonResponse(response, safe=False)