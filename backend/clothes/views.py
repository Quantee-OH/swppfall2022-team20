import json
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.contrib import auth
from django.forms.models import model_to_dict
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from json.decoder import JSONDecodeError
from django.utils import timezone
from .models import Clothes, User, Review, Comment, Size
from . import recommender

NO_USER = "존재하지 않는 유저입니다."
NO_CLOTHES = "존재하지 않는 상품입니다."

@ensure_csrf_cookie
def csrf_token(request):
    if request.method == "GET":
        return HttpResponse(status=204)
    else:
        return HttpResponseNotAllowed(["GET"])
    # Create your views here.

def signup(request):
    if request.method == 'POST':
        requestbody = json.loads(request.body)
        user = User.objects.create_user(
            username=requestbody['username'],
            password=requestbody['password'],
            nickname=requestbody['nickname'],
            email=requestbody['email'],
            length=requestbody['length'],
            waist_size=requestbody['waist_size'],
            thigh_size=requestbody['thigh_size'],
            calf_size=requestbody['calf_size']
        )

        auth.login(request,user)
        response_dict = {"session_id":request.session.session_key,"username":auth.get_user(request).get_username()}
        return JsonResponse(response_dict,status=200)
        
def login(request):
    if request.method == 'POST':
        requestbody = json.loads(request.body.decode())
        username=requestbody['username']
        password=requestbody['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request,user)
            response_dict = {"session_key":request.session.session_key,"username":user.username, "length":user.length}
            return JsonResponse(response_dict,status=200)
        else:
            response_dict = {"username":username}
            return JsonResponse(response_dict,status=401)

#모든 상품리스트 반환
def main(request, user_id):
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    if 'visit_count' not in request.session:
        user_length = int(user.length)
        user_waist = int(user.waist_size)
        user_thigh = int(user.thigh_size)
        user_calf = int(user.calf_size)
        for size in Size.objects.all():
            try:
                waist_diff = int(size.waist_size) - user_waist
                if waist_diff >= 3.0 or waist_diff < -1.0:
                    continue
                length_diff = user_length - int(size.length)
                if length_diff <= 0:
                    continue

                thigh_diff = size.thigh_size - user_thigh
                if not thigh_diff >= 1.0:
                    continue
                
                calf_diff = size.calf_size - user_calf
                if not calf_diff >= 1.0:
                    continue
            except:
                continue
            user.recommended.add(size)
        for review in Review.objects.all():
            reviewed_user_length = int(review.uploaded_user.length)
            reviewed_user_waist = int(review.uploaded_user.waist_size)
            reviewed_user_thigh = int(review.uploaded_user.thigh_size)
            reviewed_user_calf = int(review.uploaded_user.calf_size)

            length_diff = abs(user_length - reviewed_user_length)
            if not length_diff <= 2:
                continue

            waist_diff = abs(user_waist - reviewed_user_waist)
            if not waist_diff <= 2:
                continue
            
            thigh_diff = abs(user_thigh - reviewed_user_thigh)
            if not thigh_diff <= 2:
                continue
            
            calf_diff = abs(user_calf - reviewed_user_calf)
            if not calf_diff <= 2:
                continue

            review.recommended_user.add(user)
        
        request.session['visit_count'] = 1

        recommended_list = []
        prev_clothes = {"name": "name"}
        for size in user.recommended.all():
            if prev_clothes["name"] != size.clothes.name:
                recommended_list.append(prev_clothes)
                clothes = size.clothes
                clothes_data = model_to_dict(clothes)
                clothes_data = {**clothes_data, "named_size":[size.named_size]}
                prev_clothes = clothes_data
            else:
                size_list = prev_clothes["named_size"]
                size_list.append(size.named_size)
                prev_clothes["named_size"] = size_list
        recommended_list.pop(0)
        return JsonResponse(recommended_list, safe=False)
    else:
        recommended_list = []
        prev_clothes = {"name": "name"}
        for size in user.recommended.all():
            if prev_clothes["name"] != size.clothes.name:
                recommended_list.append(prev_clothes)
                clothes = size.clothes
                clothes_data = model_to_dict(clothes)
                clothes_data = {**clothes_data, "named_size":[size.named_size]}
                prev_clothes = clothes_data
            else:
                size_list = prev_clothes["named_size"]
                size_list.append(size.named_size)
                prev_clothes["named_size"] = size_list
        recommended_list.pop(0)
        request.session['visit_count'] += 1
        return JsonResponse(recommended_list, safe=False)

def profile(request, user_id):
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    if request.method == 'GET':
        return JsonResponse(
            {
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "length": user.length,
                "waist_size": user.waist_size,
                "thigh_size": user.thigh_size,
                "calf_size": user.calf_size,
                })
    if request.method == 'PUT':
        try:
            body = request.body.decode()
            user.nickname = json.loads(body)['nickname']
            user.email = json.loads(body)['email']
            user.length = json.loads(body)['length']
            user.waist_size = json.loads(body)['waist_size']
            user.thigh_size = json.loads(body)['thigh_size']
            user.calf_size = json.loads(body)['calf_size']
            user.save()
        except (KeyError, JSONDecodeError) as e:
                return HttpResponseBadRequest()
        response_dict = {'id': user.id, 'username': user.username, 'length': user.length}
        return JsonResponse(response_dict, status=200)
            
def review(request, user_id, clothes_id):
    if not (Clothes.objects.filter(id=clothes_id)).exists():
        return JsonResponse({"message": NO_CLOTHES}, status=404)
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    if request.method == 'GET':
        clothes_reviews = Review.objects.filter(reviewing_clothes_id=clothes_id)
        matched_reviews = clothes_reviews.filter(recommended_user = user)
        review_list = [review for review in matched_reviews.values()]
        return JsonResponse(review_list, safe=False, status=200)
    elif request.method == 'POST':
        clothes = Clothes.objects.get(id=clothes_id)
        try:
            body = request.body.decode()
            content = json.loads(body)['content']
        except (KeyError, JSONDecodeError) as e:
                return HttpResponseBadRequest()
        review = Review(upload_time=timezone.now(),
          content=content,
          photo="",
          reviewing_clothes=clothes,
          uploaded_user=user
          )
        review.save()
        review.recommended_user.add(user)
        review.photo = "https://stylestargram.s3.ap-northeast-2.amazonaws.com/review{}".format(review.id)
        review.save()
        response_dict = {'id': review.id, 'name': review.uploaded_user.nickname, 'content': review.content, 'photo': review.photo}
        return JsonResponse(response_dict, safe=False, status=201)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])

def comment(request, user_id, review_id):
    if not (Review.objects.filter(id=review_id)).exists():
        return JsonResponse({"message": NO_CLOTHES}, status=404)
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    review = Review.objects.get(id=review_id)
    if request.method == 'GET':
        comment_all_list = [comment for comment in review.comment_list.all().values()]
        return JsonResponse(comment_all_list, safe=False, status=200)
    elif request.method == 'POST':
        user = User.objects.get(username=user_id)
        try:
            body = request.body.decode()
            content = json.loads(body)['content']
        except (KeyError, JSONDecodeError) as e:
                return HttpResponseBadRequest()
        comment = Comment(upload_time=timezone.now(),
          content=content,
          uploaded_user=user,
          original_review=review
          )
        comment.save()
        comment_all_list = [comment for comment in review.comment_list.all().values()]
        return JsonResponse(comment_all_list, safe=False, status=201)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])

def scrap(request, user_id, clothes_id, is_scrap):
    if not (Clothes.objects.filter(id=clothes_id)).exists():
        return JsonResponse({"message": NO_CLOTHES}, status=404)
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    clothes = Clothes.objects.get(id=clothes_id)
    if is_scrap == "scrap":
        user.scrapped.add(clothes)
        return HttpResponse(status=200)
    elif is_scrap == "unscrap":
        user.scrapped.remove(clothes)
        return HttpResponse(status=200)

def scrapped_list(request, user_id):
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    scrapped_list = []
    prev_clothes = {"name": "name"}
    for clothes in user.scrapped.all():
        clothes_data = model_to_dict(clothes)
        if user.recommended.filter(clothes=clothes).exists():
            size_list = []
            for size in user.recommended.filter(clothes=clothes):
                size_list.append(size.named_size)
            clothes_data["named_size"] = size_list
        scrapped_list.append(clothes_data)
    return JsonResponse(scrapped_list, safe=False, status=200)
    scrapped_list = []
    prev_clothes = {"name": "name"}
    for size in user.recommended.all():
        if prev_clothes["name"] != size.clothes.name:
            scrapped_list.append(prev_clothes)
            clothes = size.clothes
            clothes_data = model_to_dict(clothes)
            clothes_data = {**clothes_data, "named_size":[size.named_size]}
            prev_clothes = clothes_data
        else:
            size_list = prev_clothes["named_size"]
            size_list.append(size.named_size)
            prev_clothes["named_size"] = size_list
    scrapped_list.pop(0)
    return JsonResponse(scrapped_list, safe=False)

def analyze(request, user_id, clothes_id):
    if not (Clothes.objects.filter(id=clothes_id)).exists():
        return JsonResponse({"message": NO_CLOTHES}, status=404)
    if not (User.objects.filter(username=user_id)).exists():
        return JsonResponse({"message": NO_USER}, status=404)
    user = User.objects.get(username=user_id)
    clothes_sizes = user.recommended.filter(clothes_id=clothes_id)
    analysis_dict = {}
    for clothes_size in clothes_sizes:
        named_size = clothes_size.named_size
        analysis = recommender.analyze(clothes_size, user)
        analysis_dict[named_size] = analysis
    if request.method == 'GET':
        return JsonResponse(analysis_dict, safe=False, status=200)

