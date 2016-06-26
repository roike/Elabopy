#!/usr/bin/env python
# -*- coding: utf-8 -*-
# project: elabo-one
# module: thirdpen.main 
# Copyright 2016 ryuji.oike@gmail.com
# --------------------------------------------------------

from google.appengine.ext import ndb
from google.appengine.api import taskqueue, urlfetch, memcache
from bottle import Bottle, debug, request, response, abort
import logging
from json import loads
#localモジュール---------------------------------
from controllers.blog import read_gcs
from models.blog import Channel, Blog

FORMATS = dict(jpg='image/jpeg', png='image/png', gif='image/gif')

# Create the Bottle WSGI application.

bottle = Bottle()
debug(True)

#------------Note--------------
#urlがeloabo-oneを叩くことはないので、Bookmark対応おびAnchorのfilterはthird-penでかける
#但し、dwload_imageは現状、eloabo-oneを直接叩くので改善必要

#-------decorator section-------------------------
def allow_cors(func):
    def wrapper(*args, **kwargs):

        #print "this is a decorator which enable CORS for specified endpoint."
        #Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
        response.headers['Access-Control-Allow-Origin'] = 'https://third-pen.com'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        return func(*args, **kwargs)

    return wrapper

def allow_access(func):
    def wrapper(*args, **kwargs):
        appid = request.forms.get('appid')
        token_call = request.forms.get('token')
        token = memcache.get(appid)
        if token == token_call:
            return func(*args, **kwargs)

        #if token is None or token != token_call:
        response.status = 403
        #response.content_type = 'application/json; charset=utf-8'
        return {'error': 'Forbidden, No access right.', 'status': '403'}

    return wrapper

#---------------------------------------------
@bottle.route('/thirdpen/inbound')
def get_token():
    incoming_app_id = request.headers.get('X-Appengine-Inbound-Appid', None)
    #logging.info(incoming_app_id)
    token = memcache.get(incoming_app_id)
    if token:
        return token
    channel_key = ndb.Key('Channel', incoming_app_id)
    channel = channel_key.get()
    if channel:
        token = channel.gen_access_token()
        #tokenの有効時間は2時間 更新契機はサーバ、ユーザ単位ではしない
        memcache.add(key=incoming_app_id, value=token, time=3600)
        return token
    
    else:
        response.status = 403
        return {'error': 'Forbidden, No access right.'}
    
@bottle.route('/thirdpen/dwload/<filename>')
@allow_cors
def dwload_image(filename):
    img_format = filename.split('.')[-1]
    content_type = FORMATS.get(img_format)
    if content_type:
        response.headers['Content-Type'] = content_type
        return read_gcs(filename)


#---dynamic module section---------------------
@bottle.route('/thirdpen/blog/<abcd>/<slug>', method='post')
@allow_cors
@allow_access
def fetch_blog(abcd, slug):
    try:
        blog = ndb.Key(Blog, '%s_%s' % (abcd, slug)).get()
        return {'publish': blog.get_blog()}

    except Exception as e:
        loging.error(e)
        abort(500)

@bottle.route('/thirdpen/newist', method='post')
@allow_cors
@allow_access
def entry_newist():
    try:
        params = {'posted': True}
        params.update(request.forms)
        cb = 'entry'
        if params['channel'] == 'home':
            cb = 'home'
        return {'publish': Blog.newist(params, cb)}
    except Exception as e:
        logging.error(e)
        abort(500)


#---utility section------------------------------

def send_mail(nickname):
    #login mail送信
    taskqueue.Task(
            url='/master/mail/login', 
            params={'result': u'login', 'name': nickname}
            ).add('master')


