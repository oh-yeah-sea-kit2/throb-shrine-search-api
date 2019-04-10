#!/usr/local/bin/python
import json
import os
import yaml
# pip install pyyaml
# from flask import Blueprint
from flask import Flask
from flask import abort, jsonify, request
import riak
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
mydir = os.path.dirname(os.path.abspath(__file__))

bucket_type = "shrine"
version = '1.1'
error_msg = None

# riak server
riak_nodes=[]
with open( mydir + '/riak-host.yaml' ) as file:
  riak_nodes = yaml.load(file)
client = riak.RiakClient(nodes = riak_nodes)

# config
conf = {}
with open( mydir + '/shrine-conf.yaml' ) as file:
  conf = yaml.load(file)


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# app = Blueprint("app", __name__, url_prefix="/path")

# def get_point_query(client, data_name, b_lon, e_lon, b_lat, e_lat):
#   bucket = client.bucket_type(bucket_type).bucket(data_name)
#   # lat
#   lat_keys = bucket.get_index('lat_int', b_lat, e_lat)
#   # lon
#   lon_keys = bucket.get_index('lon_int', b_lon, e_lon)
#   # ２つのキーで重複チェック
#   keys = set(lat_keys) & set(lon_keys)
#   # 続きはここから
#   result = []
#   for key in keys:
#     obj = bucket.get(key)
#     result.append(obj.data)
#   return result

def get_bucket_key(data_name, key):
  # res = []
  bucket = client.bucket_type(bucket_type).bucket(data_name)
  obj = bucket.get(key)
  return obj.data

def wrapper_get_bucket_key(args):
  return get_bucket_key(*args)

def thread_get_bucket_keys(get_key_list):
  result = []
  worker_num = 100  # ワーカースレッド数

  with ThreadPoolExecutor(worker_num) as executer:
    for k in get_key_list:
      result.append(executer.submit(wrapper_get_bucket_key, k))
  # pprint.pprint(result)
  res = []
  for x in as_completed(result):
    res.append(x.result())
  return res

def get_point_query(client, data_name, b_lon, e_lon, b_lat, e_lat):
  bucket = client.bucket_type(bucket_type).bucket(data_name)
  # lat
  lat_keys = bucket.get_index('lat_int', b_lat, e_lat)
  # lon
  lon_keys = bucket.get_index('lon_int', b_lon, e_lon)
  # ２つのキーで重複チェック
  keys = set(lat_keys) & set(lon_keys)
  print("keys lenght: {}".format(len(keys)))
  # result = []
  get_key_list = [(data_name, key) for key in keys]
  results = thread_get_bucket_keys(get_key_list)
  # for key in keys:
  #   obj = bucket.get(key)
  #   result.append(obj.data)
  return results

def conv_range(lat, lon, ran):
  lat_m = 0.000008983148616
  lon_m = 0.000010966382364
  b_lon = int((float(lon) - (int(ran) * lon_m)) * 100000)
  e_lon = int((float(lon) + (int(ran) * lon_m)) * 100000)
  b_lat = int((float(lat) - (int(ran) * lat_m)) * 100000)
  e_lat = int((float(lat) + (int(ran) * lat_m)) * 100000)

  return b_lon, e_lon, b_lat, e_lat

def check_value(value, value_name, conf):
  global error_msg
  if (conf[value_name]['max'] < float(value)) or (float(value) < conf[value_name]['min']):
    error_msg = 'value out of range'
    abort(400)
  # print("check_value: {}, {}".format(value_name, value))

def format_shrine_data(data):
  res = []
  for d in data:
    r = {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          d['lon'],
          d['lat']
        ]
      },
      "properties": {
        "address": d['address'],
        "name": d['name'],
        "googlemaps_url": 'http://maps.google.com/maps?q={},{}'.format(d['lat'], d['lon']),
        "url": d['url'],
      }
    }
    res.append(r)
  return res

def get_master_data(lat, lon, ran):
  global error_msg
  # ?lat=35.7237483&lon=139.7557801
  if (lat == ''):
    error_msg = "lat must be set."
    abort(400)
  if (lon == ''):
    error_msg = "lon must be set."
    abort(400)
  # オプションチェック
  # lat,lon,rangeは範囲内であること
  check_value(lat, 'lat', conf)
  check_value(lon, 'lon', conf)
  check_value(ran, 'range', conf)
  
  # 緯度の範囲
  # 経度の範囲
  b_lon, e_lon, b_lat, e_lat = conv_range(lat, lon, ran)
  time_count = time.time()
  data = get_point_query(client, 'master', b_lon, e_lon, b_lat, e_lat)
  print("get_point_query: {}".format(time.time()-time_count))
  data = format_shrine_data(data)
  req = {
    "type": "FeatureCollection",
    "counts": len(data),
    "features": data,
    # 'header': len(data),
    # 'response': data,
  }
  # ret = jsonify(req)
  ret = json.dumps(req, sort_keys=True, indent=None, ensure_ascii=False)
  # ret += "\n"
  return ret
  

# http://0.0.0.0:5000/master?lat=35.7237483&lon=139.7557801
# 緯度経度と半径を指定し、その範囲のデータを返す
@app.route("/shrine/master", methods=['GET', 'POST'])
def get_master():
  lat = request.values.get("lat", '')
  lon = request.values.get("lon", '')
  ran = request.values.get("range", 10000)
  ret = get_master_data(lat, lon, ran)
  return ret

def get_latlon_from_zipcode(zipcode):
  data = get_bucket_key('zipcode', zipcode)
  if data is None:
    return '', ''
  lat = data['Lat']
  lon = data['Lon']
  return lat, lon

@app.route("/shrine/zipcode", methods=['GET', 'POST'])
def get_zipcode_lonlat():
  global error_msg
  zipcode = request.values.get("zipcode", '')
  ran = request.values.get("range", 10000)
  if (zipcode == ''):
    error_msg = "zipcode must be set."
    abort(400)
  if (len(zipcode) != 7):
    error_msg = "Please enter the zip code with 7 digits."
    abort(400)
  lat, lon = get_latlon_from_zipcode(zipcode)
  ret = get_master_data(lat, lon, ran)
  return ret


@app.route("/shrine/version", methods=['GET', 'POST'])
def get_version():
  response = jsonify({'version': version, 'result': True})
  return response

@app.errorhandler(404)
# def error_handler(404):
#   response = jsonify({'message': 404, 'result': False})
#   return response, 404
@app.errorhandler(404)
def error_handler_404(error):
  response = jsonify(
    {
      'id': error.description,
      'message': error_msg,
      'result': error.code
    }
  )
  return response, error.code

@app.errorhandler(400)
def error_handler_400(error):
  response = jsonify(
    {
      'id': error.description,
      'message': error_msg,
      'result': error.code
    }
  )
  return response, error.code

if __name__ == "__main__":
  app.debug = True
  app.run(host='0.0.0.0', port=5000)

  
