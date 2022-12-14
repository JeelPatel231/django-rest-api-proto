from rest_framework.decorators import api_view
from rest_framework import permissions,status
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from djangorest import settings
import datetime
import jwt

from .models import User
from .serializers import UserSerializer
from django.contrib.auth.hashers import make_password

@api_view(["GET"])
def get_all_users(req):
    data = User.objects.all()
    serializer = UserSerializer(data,many=True)
    return Response(serializer.data)

@api_view(["POST"])
def insert_user(req):
    user = UserSerializer(data=req.data)
    if not user.is_valid():
        return Response(user.errors,status=status.HTTP_400_BAD_REQUEST)

    user.save()
    return Response(status=status.HTTP_200_OK)

@api_view(["POST"])
def login_user(req):
    username = req.data['username']
    password = req.data['password']
    user = User.objects.filter(username=username).first()

    if user is None:
        return Response("Account Not Found",status=status.HTTP_401_UNAUTHORIZED)
        
    if not check_password(password, user.password):
        return Response("Wrong Password",status=status.HTTP_401_UNAUTHORIZED)

    payload = {
        'username': user.username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=60),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    response = Response()
    response.set_cookie(key='jwt', value=token, httponly=True)
    response.data = {'jwt': token}
    return response

@api_view(["POST"])
def logout_user(req):
    response = Response()
    response.delete_cookie('jwt')
    response.status_code = status.HTTP_200_OK
    return response

@api_view(["GET"])
def get_user(req):
    token = req.COOKIES.get('jwt')
    if not token:
        return Response("Unauthenticated", status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return Response("Expired Token", status=status.HTTP_401_UNAUTHORIZED)

    user = User.objects.filter(username=payload['username']).first()
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(["POST"])
def change_password(req):
    token = req.COOKIES.get('jwt')

    if not token:
         return Response("Unauthenticated", status=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return Response("Expired Token", status=status.HTTP_401_UNAUTHORIZED)

    new_pass = req.data.get('password')
    if new_pass is None:
        return Response("Password Not Supplied", status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(username=payload['username']).first()

    # User.objects.filter(...).first() may return None
    # but we are decoding username from JWT, meaning the user MUST EXIST
    assert user is not None

    user.password = make_password(new_pass)
    user.save()

    return Response(status=status.HTTP_200_OK)
