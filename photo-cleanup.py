import re
import sys
import os.path
import hashlib
import json
import requests
from datetime import datetime
import pytz
from geopy.distance import geodesic
from pyexiftool import exiftool

class Photo:
  def __init__(self):
    self.md5 = ""
    self.working_filename = ""
    self.base_filename = ""
    self.extension = ""
    self.dirname = ""
    self.metadata = {}
    self.date_taken = ""
    self.latitude = ""
    self.longitude = ""
    self.duplicate_filenames = []

class PhotoBucket:
  def __init__(self):
    self.date_taken = ""
    self.bucket_name = ""
    self.latitude = ""
    self.longitude = ""
    self.photos = []

# Path to exiftool
EXIFTOOL_PATH = r".\pyexiftool\exiftool(-k).exe"
et = exiftool.ExifTool(EXIFTOOL_PATH)
et.start()

# Radius in Miles for photos to be in the "same spot"
RADIUS_MILES = 2

# Default Latitude/Longitude
DEFAULT_LATITUDE = 38.0406
DEFAULT_LONGITUDE = -84.5037

# Directory to Walk
PATH = sys.argv[1]

md5_list = []
photos = {}
photo_buckets = []
live_videos = []

# Walk through the directory
for (root, dirnames, filenames) in os.walk(PATH):
  # for dirname in dirnames:
  for filename in filenames:
    file = root + "\\" + filename
    md5 = hashlib.md5(open(file,'rb').read()).hexdigest()
    # md5 = file
    metadata = et.get_metadata(file)

    if md5 in md5_list:
      matching_photo = photos[md5] 
      matching_photo.duplicate_filenames.append(file)
    else:
      photo = Photo()
      photo.md5 = md5
      photo.working_filename = file
      photo.base_filename = filename
      photo.extension = re.findall('\w+', filename)[-1]
      photo.dirname = root
      photo.metadata = metadata
      print(photo.extension + "\t" + file)
      date_taken = ""
      latitude = ""
      longitude = ""
      live_video = False
      if photo.extension.lower() == "jpg" or photo.extension.lower() == "jpeg":
        date_taken = metadata.get("EXIF:DateTimeOriginal", datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y:%m:%d %H:%M:%S")) + metadata.get("EXIF:OffsetTimeOriginal", '-04:00')
        latitude = metadata.get("Composite:GPSLatitude", DEFAULT_LATITUDE)
        longitude = metadata.get("Composite:GPSLongitude", DEFAULT_LONGITUDE)
      elif photo.extension.lower() == "png":
        date_taken = metadata.get("EXIF:DateTimeOriginal", datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y:%m:%d %H:%M:%S")) + "-04:00"
        latitude = DEFAULT_LATITUDE
        longitude = DEFAULT_LONGITUDE
      elif photo.extension.lower() == "mov":
        if metadata.get("QuickTime:Live-photoAuto") == 1 or metadata.get("QuickTime:ContentIdentifier", "") != "":
          live_video = True
        date_taken = metadata.get("QuickTime:CreationDate", datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y:%m:%d %H:%M:%S%z"))
        latitude = metadata.get("Composite:GPSLatitude", DEFAULT_LATITUDE)
        longitude = metadata.get("Composite:GPSLongitude", DEFAULT_LONGITUDE)
      elif photo.extension.lower() == "mp4":
        date_taken = metadata.get("QuickTime:CreateDate", datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime("%Y:%m:%d %H:%M:%S")) + "-04:00"
        latitude = metadata.get("Composite:GPSLatitude", DEFAULT_LATITUDE)
        longitude = metadata.get("Composite:GPSLongitude", DEFAULT_LONGITUDE)
      else:
        continue

      for (key, value) in metadata.items():
        print("\t" + str(key) + "\t" + str(value))

      if date_taken == "":
        photo.date_taken = datetime.now
      else:
        photo.date_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S%z')

      photo.latitude = latitude
      photo.longitude = longitude

      if live_video:
        if not os.path.isdir(PATH + "/Live_Videos"):
          os.mkdir(PATH + "/Live_Videos")
        os.rename(file, PATH + "/Live_Videos/" + photo.base_filename)
      else:
        photos[md5] = photo
        md5_list.append(md5)

if not os.path.isdir(PATH + "/Duplicates"):
  os.mkdir(PATH + "/Duplicates")

for (md5, photo) in photos.items():
  print(photo.working_filename)
  for(duplicate) in photo.duplicate_filenames:
    os.rename(duplicate, PATH + "/Duplicates/" + photo.base_filename)
  buckets = list(filter(lambda x: x.date_taken.strftime("%Y_%m_%d") == photo.date_taken.strftime("%Y_%m_%d") and geodesic((x.latitude, x.longitude), (photo.latitude, photo.longitude)).miles < RADIUS_MILES, photo_buckets))
  if len(buckets) > 0:
    print("Distance " + str(geodesic((buckets[0].latitude, buckets[0].longitude), (photo.latitude, photo.longitude)).miles) + " " + str(geodesic((buckets[0].latitude, buckets[0].longitude), (photo.latitude, photo.longitude)).miles < RADIUS_MILES))
    buckets[0].photos.append(photo)
    print("\t" + "Existing Bucket " + str(buckets[0].bucket_name) + " " + str(len(buckets[0].photos)))
  else:
    bucket = PhotoBucket()
    bucket.date_taken = photo.date_taken
    bucket.bucket_name = bucket.date_taken.strftime("%Y_%m_%d") + " Photos_" + str(round(photo.latitude, 4)) + "_" + str(round(photo.longitude, 4))
    bucket.latitude = photo.latitude
    bucket.longitude = photo.longitude
    bucket.photos.append(photo)
    photo_buckets.append(bucket)
    print("\t" + "New Bucket " + str(bucket.bucket_name) + " " + str(len(bucket.photos)))

for bucket in photo_buckets:
  if not os.path.isdir(PATH + "/" + bucket.bucket_name):
    os.mkdir(PATH + "/" + bucket.bucket_name)
  for photo in bucket.photos:
    os.rename(photo.working_filename, PATH + "/" + bucket.bucket_name + "/" + photo.base_filename)

et.terminate()