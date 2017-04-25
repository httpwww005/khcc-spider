# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
#from scrapy.pipelines.images import ImagesPipeline
import os
from imgurpython import ImgurClient
import time
import scrapy
import logging
from datetime import datetime
import urlparse

logger = logging.getLogger(__name__)

class ImgurPipeline(object):
    def imgur_init(self):
        imgur_id = os.environ.get('IMGUR_ID', "")
        imgur_secret = os.environ.get('IMGUR_SECRET', "")
        if self.imgur_anonymous:
            self.imgur_client = ImgurClient(
                    imgur_id, 
                    imgur_secret)
        else:
            imgur_refresh_token = os.environ.get('IMGUR_REFRESH_TOKEN', "")
            self.imgur_client = ImgurClient(
                    imgur_id, 
                    imgur_secret, 
                    refresh_token=imgur_refresh_token)


    def create_album(self):
        date_str = str(datetime.now().date())
        album = self.imgur_client.create_album({"title":"KHCC 眷村以住代護計畫 %s"%date_str})
        self.album = album
        logger.debug('album: %s' % album)
        
        if self.imgur_anonymous:
            return self.album["deletehash"]
        else:
            return self.album["id"]


    def open_spider(self, spider):
        self.upload_image = spider.upload_image
        self.imgur_album_id = spider.imgur_album_id
        self.imgur_delay = spider.imgur_delay # upload limit, 1 hour 50 images, 60/50=1.2
        self.imgur_anonymous = spider.imgur_anonymous
        self.url_base = spider.url_base

        if(self.upload_image):
            self.imgur_init()

            if not self.imgur_album_id:
                self.imgur_album_id = self.create_album()

        logger.debug('upload_image: %s' % self.upload_image)
        logger.debug('imgur_album_id: %s' % self.imgur_album_id)
        logger.debug('imgur_delay: %d' % self.imgur_delay)
        logger.debug('imgur_anonymous: %s' % self.imgur_anonymous)


    def process_item(self, item, spider):
        if not self.upload_image:
            return item

        if item["location"] == u"左營":
            abbr = "ZY"
        else:
            abbr = "FS"

        imgur_urls = []
        images = []
        for i in range(0, len(item['image_urls'])):
            url = urlparse.urljoin(self.url_base, item['image_urls'][i])
            address = item["address"].replace("-","_")
            desc = "%s\n#%s%s" % (url, abbr, address)
	    config = {
		'album': self.imgur_album_id,
		'title': "%s %s %02d" % (item['location'], item['address'], i+1),
		'description': desc
	    }

            retry_count = 5

            while retry_count > 0:
                image = None
                try:
                    image = self.imgur_client.upload_from_url(
                            url=url, 
                            config=config, 
                            anon=self.imgur_anonymous)
                except Exception as e:
                    logger.debug(e)
                    logger.debug('sleep %d seconds and retry upload_from_url(): %d' % 
                            (self.imgur_delay, retry_count))

                    retry_count -= 1

                    try:
                        time.sleep(self.imgur_delay)
                    except:
                        spider.close_down = True # not work

                    continue


                if image:
                    logger.debug('image: %s' % image)

                    deletehash = image["deletehash"]
                    image_id = image["id"]
                    original_url = item['image_urls'][i]

                    detail = {
                            "deletehash":deletehash,
                            "id":image_id,
                            "original_url":original_url}

                    images.append(detail)
                    logger.debug('sleep for %d secodes..' % self.imgur_delay)

                    try:
                        time.sleep(self.imgur_delay)
                    except:
                        spider.close_down = True # not work

                break


        del item["image_urls"]

        item["images"] = images

        return item
