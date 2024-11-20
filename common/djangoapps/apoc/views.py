from util.json_request import expect_json, JsonResponse

from django.http import HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
#from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from edxmako.shortcuts import render_to_response

from django.contrib.auth.models import User
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from student.models import ApocStatus,ApocScore
import datetime
import logging
AUDIT_LOG = logging.getLogger("audit")
from pprint import pformat

#check if user exist
from student.models import UserProfile


def isExist(user_id):
        AUDIT_LOG.info("in isExist method")
	check_user = True

	try:
		check = User.objects.all().get(pk=user_id)
	except:
		check_user = False
	return check_user

#set status
def setstatus(user_id,first,status=0,score=0):
	# check if user exist:
	check_user = isExist(user_id)
	data = {}
	timestamp = datetime.datetime.now()
	if not check_user:
		data['answer'] = False
		data['user_status'] = check_user
	else:
                userprofile = UserProfile.objects.get(user=User.objects.all().get(pk=user_id))
                city = userprofile.city
		# check if a row exist
		check_status = True
		try:
			current = ApocStatus.objects.get(user_id=user_id)
			# get actual current_stage value
			current_status = current.current_stage
			data['current_stage'] = current_status
			# if new value is diffent than the actual value
			if current_status != status and first != True and current_status != 2:
				current.current_stage = status
				current.score = current.score
				current.timestamp = timestamp
				current.save()
				data['answer'] = True
		except:
			check_status = False
		# if not rows also, created a new one
		if not check_status:
			###TODO: CHANGE STAGES MAPPING
			if current_stage in [4,6,7,8]:
				# FOR STAGES THAT BELONG TO MAIN SCORE
				b = ApocStatus(user_id=user_id,current_stage=status,score=score,timestamp = timestamp,scorebis=0)
				b.save()
				data['answer'] = True
			else:
				# FOR STAGES THAT BELONG TO SCOREBIS
				b = ApocStatus(user_id=user_id,current_stage=status,score=0,timestamp = timestamp,scorebis=score)
				b.save()
				data['answer'] = True

	if first != None:
		### MAIN SCORE
		all_users = ApocStatus.objects.order_by('-score','-timestamp')
		trio = []
		y = 0
                z = 0
		#all_users_number = UserProfile.objects.get(city=city).count()
                all_users_number = all_users.count()
		while y < all_users_number:
                        user_other_id = all_users[y].user_id
                        #If the other user if of the same company (=city) and the trio is not full yet, add him
			if len(trio) < 3 and UserProfile.objects.get(user=User.objects.all().get(pk=user_other_id)).city == city:
				username = User.objects.all().get(pk=user_other_id).username
				trio.append(username)
                        if UserProfile.objects.get(user=User.objects.all().get(pk=user_other_id)).city == city:
                                z = z + 1
			if user_id == all_users[y].user_id:
				data['position'] = z
			y = y +1
		data['trio'] = trio
		data['user_id'] = user_id
		### SECONDARY SCORE
		all_users = ApocStatus.objects.order_by('-scorebis','-timestamp')
		triobis = []
		y = 0
                z = 0
		all_users_number = all_users.count()
                #all_users_number = UserProfile.objects.get(city=city).count()
		while y < all_users_number:
                        user_other_id = all_users[y].user_id
                        if len(triobis) < 3 and UserProfile.objects.get(user=User.objects.all().get(pk=user_other_id)).city == city:
                                username = User.objects.all().get(pk=user_other_id).username
				triobis.append(username)
                        if UserProfile.objects.get(user=User.objects.all().get(pk=user_other_id)).city == city:
                                z = z + 1
			if user_id == all_users[y].user_id:
				data['positionbis'] = z
			y = y +1
		data['triobis'] = triobis
		data['user_id'] = user_id
	return data

def setscore(user_id,first,stage_id,stage_status,stage_score):
	check_user = isExist(user_id)
	if not check_user:
		return {'answer':False,'status':check_user}
	else:
		i = 0
		score_total = 0
		score_totalbis = 0
		score_array = []
		total = int
		position = int
		timestamp = datetime.datetime.now()
		while i < 8:
			i = i + 1
			try:
				### IF THERE IS A SCORE RECORDED ON THE STAGE
				score = ApocScore.objects.get(user_id=user_id,stage_id=i)
				q = {'stage_id':i,'status':0,'score':0}
				if ((score.stage_score is None) or (score.stage_id is None)) or ((score.stage_score != stage_score) or (score.stage_status != stage_status)) and (score.stage_status != 2) and (score.stage_score < 1) and score.stage_id == stage_id and first != True:
					score.stage_score = stage_score
					score.stage_status = stage_status
					score.stage_accessed = timestamp
					score.save()
					###TODO: SCORE TOTAL IS THE SUM ONLY IF STAGE IS IN
					if i in [4,6,7,8]:
						 score_total = score_total + stage_score
					else:
						score_totalbis = score_totalbis + stage_score
					q = {'stage_id':i,'status':stage_status,'score':stage_score}
					score_array.append(q)
				else:
					if score.stage_score is None:
						q['score'] = 0
						###TODO: SCORE TOTAL IS THE SUM ONLY IF STAGE IS IN
						if i in [4,6,7,8]:
							score_total = score_total + 0
						else:
							score_totalbis = score_totalbis + 0
					else:
						q['score'] = score.stage_score
						###TODO: SCORE TOTAL IS THE SUM ONLY IF STAGE IS IN
						if i in [4,6,7,8]:
							score_total = score_total + score.stage_score
						else:
							score_totalbis = score_totalbis + score.stage_score
					if score.stage_status is None:
						q['status'] = 0
					else:
						q['status'] = score.stage_status
					score_array.append(q)
				try:
					user_status = ApocStatus.objects.get(user_id=user_id)
					user_status.score = score_total
					user_status.scorebis = score_totalbis
					user_status.timestamp = timestamp
					user_status.save()
				except:
					user_status = None
			except:
				## IF THERE WAS NO SCORE FOR THE STAGE
				q = {'stage_id':i,'status':0,'score':0}
				score_array.append(q)
				try:
					score = ApocScore.objects.get(user_id=user_id,stage_id=i)
				except:
					b = ApocScore(user_id=user_id,stage_id=i,stage_status=0,stage_score=0,stage_begin=timestamp,stage_last_accessed = timestamp)
					b.save()
		return {'score_detail':score_array,'score_total':score_total,'score_totalbis':score_totalbis}

# set score

#@ensure_csrf_cookie
@csrf_exempt
def status_and_score(request):
	# check request method
	if request.method == 'POST':
		requete = request.POST
		user_id = requete.get('user_id')
		user_id = int(user_id)
                AUDIT_LOG.info(u"USERID IN STATUS AND SCORE: "+pformat(user_id))
                AUDIT_LOG.info(u"USERNAME IN STATUS AND SCORE: "+pformat(User.objects.all().get(pk=user_id).username))
		score = requete.get('total_score')
		score = float(score)
		stage_status = requete.get('status')
		stage_id = requete.get('etape_id')
		stage_id = int(stage_id)
		stage_score = requete.get('etape_score')
		stage_score = float(stage_score)
		first = False
		set_score = setscore(user_id,first,stage_id,stage_status,stage_score)
		set_status = setstatus(user_id,first,stage_id,score)
		user = User.objects.all().get(pk=user_id)
		username = user.username
		first_name = user.first_name
		last_name = user.last_name
		avatar = get_profile_image_urls_for_user(user)['medium']
		user_info = {'username':username,'first_name':first_name,'last_name':last_name,'avatar':avatar}
		# creation dict de retour
		data = {'user':user_info,'score':set_score,'status':set_status}	
		# creation call de retour
		reponse = JsonResponse(data)
		# set the cookie
		reponse.set_cookie('cookie_apoc', data)
		return reponse


@csrf_exempt
@require_http_methods(("POST"))
def current_stage(request):
	# check request method
	if request.method == 'POST':
		requete = request.POST
		user_id = requete.get('user_id')
		user_id = int(user_id)
		stage_id = requete.get('etape_id')
		stage_id = int(stage_id)
		first = False
		check_user = isExist(user_id)
		data = {}
		timestamp = datetime.datetime.now()
		if not check_user:
			data['answer'] = False
	else:
		timestamp = datetime.datetime.now()
		try:
			i = 0
			while i<9:
				i = i + 1
				score = ApocScore.objects.get(user_id=user_id,stage_id=i)
				if score.stage_id == stage_id:
					score.stage_status = 1
					score.save()
					user_status = ApocStatus.objects.get(user_id=user_id)
					user_status.current_stage = stage_id
					user_status.save()
					data['answer'] = True
		except:
			data['answer'] = False
	return data
