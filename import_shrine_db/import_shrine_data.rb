#!/usr/local/bin/ruby
require 'json'
require 'yaml'
require 'pp'
require 'parallel'
require 'time'

# gem install riak-client
require 'riak'
bucket_type = 'shrine'

riak_host = File.open('conf/riak-host.yml', 'r') { |f| YAML.safe_load(f) }


st = Time.new
import_file = ARGV[0]

def import_riak(bucket, shrine_id, info, idx)
  obj = bucket.get_or_new(shrine_id)
  obj.indexes = {}
  obj.data = info
  idx.each do |k, v|
    if v.nil?
      obj.indexes[k] = []
      next
    end
    obj.indexes[k] = [v]
  end
  obj.store
end

def read_json(file_path)
  json_data = {}
  File.open(file_path) do |io|
    json_data = JSON.parse(io.read)
  end
  json_data
end

client = Riak::Client.new(:nodes => riak_host)
bucket = client.bucket_type(bucket_type).bucket('master')

json_data = read_json(import_file)
# json_data.each do |shrine_id, info|
Parallel.each(json_data.keys, :in_threads=>100) do |shrine_id|
  info = json_data[shrine_id]
  if info['post_id'].nil?
    post_code = nil
  else
    post_code = info['post_id'].delete('-').to_i
  end
  # 緯度経度の精度的に4桁で10m程度なので5桁まで採用
  if [info['lat'], info['lon']].include?(nil)
    lat = nil
    lon = nil
  else
    lat = (info['lat'] * 10**5).to_i
    lon = (info['lon'] * 10**5).to_i
  end
  idx = {
    'post_code_int': post_code,
    'lat_int': lat,
    'lon_int': lon,
    'type_bin': 'shrine'
  }
  import_riak(bucket, shrine_id.to_s, info, idx)
end
puts "end time: #{Time.new - st}"