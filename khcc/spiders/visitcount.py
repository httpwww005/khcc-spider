# -*- coding: utf-8 -*-
import sys
import scrapy
import urlparse
import urllib
import re
import os
import datetime
from scrapy.utils.project import get_project_settings
import pytz

TZ=pytz.timezone("Asia/Taipei")


class VisitcountSpider(scrapy.Spider):
    name = "visitcount"
	
    allowed_domains = ["http://khvillages.khcc.gov.tw"]
    url_base = "http://khvillages.khcc.gov.tw/"

    def __init__(self, 
            upload_image="n", 
            chrome_spider="n", 
            imgur_anonymous="y",
            imgur_album_id=None, 
            data_least=0,
            imgur_delay=0):

        self.created_on = datetime.datetime.now(TZ)

        if upload_image == "y":
            self.upload_image = True
        else:
            self.upload_image = False

        if imgur_anonymous == "y":
            self.imgur_anonymous = True
        else:
            self.imgur_anonymous = False

        if chrome_spider == "y":
            self.is_chromespider = True
        else:
            self.is_chromespider = False

        self.imgur_delay = int(imgur_delay)

        self.data_least = int(data_least)
        
        self.imgur_album_id = imgur_album_id

        self.url_pat1 = 'http://khvillages.khcc.gov.tw/home02.aspx?ID=$4001&IDK=2&AP=$4001_SK--1^$4001_SK2--1^$4001_PN-%d^$4001_HISTORY-0'
        self.url_pat2 = 'http://khvillages.khcc.gov.tw/home02.aspx?ID=$4011&IDK=2&AP=$4011_SK-^$4011_SK2--1^$4011_PN-%d^$4011_HISTORY-0'
        self.url_pat1_index = 1
        self.url_pat2_index = 1
        self.url_pats = [self.url_pat1, self.url_pat2]

        if self.is_chromespider:
            from selenium import webdriver
            chrome_bin_path = os.environ.get('CHROME_BIN', "")
            webdriver.ChromeOptions.binary_location = chrome_bin_path
            self.driver = webdriver.Chrome()
            entry_url = ["http://khvillages.khcc.gov.tw/home02.aspx?ID=$4002&IDK=2&EXEC=L&AP=$4002_SK3-115", "http://khvillages.khcc.gov.tw/home02.aspx?ID=$4012&IDK=2&EXEC=L"]
            for url in entry_url:
                self.driver.get(url)
    

    def start_requests(self):
        for p in self.url_pats:
            url = p % 1
            yield scrapy.Request(url=url, callback=self.parse_url, dont_filter=True)


    def parse_url(self, response):

        if self.is_chromespider:
            self.driver.get(response.url)
            ax = self.driver.find_elements_by_xpath("//a")
        else:
            ax = response.xpath("//a")

        hrefs = []
        for a in ax:
            if self.is_chromespider:
                href = a.get_attribute("href")
            else:
                try:
                    href = a.xpath("./@href")[0].extract()
                except:
                    pass

            if href:
                hrefs.append(href)


        hrefs = [url for url in hrefs if(("DATA=" in url) and ("_HISTORY-" in url))]


        if len(hrefs) > 0:
            comp = re.compile("^.*DATA=(\d+)&AP.*$")
            urls = []

            for href in hrefs:
                m = comp.match(href)
                if m:
                    url = None
                    data = int(m.group(1))
                    if data >= self.data_least:
                        if self.is_chromespider:
                            url = href
                        else:
                            url = urlparse.urljoin(self.allowed_domains[0], href)

                        meta = {"data":data}

                        if self.upload_image:
                            yield scrapy.Request(url=url, 
                                    callback=self.parse_img, 
                                    meta=meta, 
                                    dont_filter=True)
                        else:
                            yield scrapy.Request(url=url, 
                                    callback=self.parse, 
                                    meta=meta, 
                                    dont_filter=True)
             
            if "4001_HISTORY" in response.url:
                self.url_pat1_index += 1
                next_url = self.url_pat1 % self.url_pat1_index
            else:
                self.url_pat2_index += 1
                next_url = self.url_pat2 % self.url_pat2_index

            yield scrapy.Request(url=next_url, callback=self.parse_url, dont_filter=True)


    def parse(self, response):
        location_1 = response.xpath("//meta[@name='DC.Title']/@content")[0].extract()

        if u"左營" in location_1:
            location = u"左營"
        else:
            location = u"鳳山"

        self.logger.debug('location: %s' % location)

        address_1 = response.xpath("//meta[@name='DC.Subject']/@content")[0].extract() 
        address = re.match(ur".*村(.*)$",address_1).group(1)
        self.logger.debug('address: %s' % address)

        count_1 = response.xpath("//span[@style='color:#a4a4a4']/text()")[0].extract()
        count = re.match(ur".*已有(.*)人瀏覽.*$",count_1).group(1)
        self.logger.debug('count: %s' % count)

        yield {'location':location,
                'address':address,
                'count':count,
                'created_on':self.created_on
                }    
        

    def parse_img(self, response):
        location_1 = response.xpath("//meta[@name='DC.Title']/@content")[0].extract()

        if u"左營" in location_1:
            location = u"左營"
        else:
            location = u"鳳山"

        self.logger.debug('location: %s' % location)

        address_1 = response.xpath("//meta[@name='DC.Subject']/@content")[0].extract() 
        address = re.match(ur"^[^\d]+([\d-]+).*$",address_1).group(1)

        self.logger.debug('address: %s' % address)

        xpath_img = "//img[@alt='%s']/@src" % address
        image_urls = response.xpath(xpath_img).extract()
        self.logger.debug('image_urls: %s' % image_urls)
        image_urls = [urllib.quote(x.encode("utf-8")) for x in image_urls if x]
        data = response.meta['data']
    
        yield {'location':location,
                'address':address,
                'created_on':self.created_on,
                'data':data,
                'image_urls':image_urls
                }
