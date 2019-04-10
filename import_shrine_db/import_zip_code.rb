#!/usr/local/bin/ruby
require 'riak'
require 'pp'
require 'csv'
require 'parallel'
riak_host_yaml = 'conf/riak-host.yml'

$riak_host = File.open(riak_host_yaml, 'r') {|f| YAML.safe_load(f)}

bucket_type = 'shrine'
bucket_name = 'zipcode'

zip_code_file = ARGV[0]

zcf = CSV.read(zip_code_file, headers: true)
zip_hash = {}
zcf.each do |f|
  zipcode = f[0]
  zip_hash[zipcode] = {
    'Zip':  f['Zip'],
    'Pre':  f['Pre'],
    'City': f['City'],
    'Addr': f['Addr'],
    'Lon':  f['Lon'].to_f,
    'Lat':  f['Lat'].to_f,
  }
end

client = Riak::Client.new(:nodes => $riak_host)
bucket = client.bucket_type(bucket_type).bucket(bucket_name)

def delete_riak(bucket)
  key_list = bucket.get_index('type_bin', 'zipcode')
  Parallel.each(key_list, :in_threads=> 100) do |key|
  # key_list.each do |key|
    bucket.delete(key)
  end
  key_list = bucket.get_index('type_bin', 'zipcode')
  pp key_list
end

Parallel.each(zip_hash.keys, :in_threads=> 100) do |zipcode|
# zip_hash.keys.each do |zipcode|
  idx = {
    'type_bin': 'zipcode',
    'pre_bin': zip_hash[zipcode]['Pre'],
    'city_bin': zip_hash[zipcode]['City']
  }
  obj = bucket.get_or_new(zipcode)
  obj.indexes = {}
  obj.data = zip_hash[zipcode]
  idx.each {|k, v| obj.indexes[k] = [v]}
  obj.store
  # exit
end
