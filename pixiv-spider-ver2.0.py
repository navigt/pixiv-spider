#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Author:  Zyue
# Time: 2020.01.30

# requeset.get的cookie设置是 'Cookie'！！！！
# 靠调试好久 我一直填的是Cookies！！！
# 变量名一定要填对

import requests
import os
from lxml import etree
import re
from contextlib import closing
import urllib
from multiprocessing import Pool
import time


class pixiv:
    def __init__(self, author_id, Cookie):
        self.author_id = author_id
        self.author_name = ''
        self.url_path_name = ''
        self.proxies = {"http": "http://127.0.0.1:10809",
                        "https": "http://127.0.0.1:10809"}
        self.BaseHeader = {
            'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/76.0.3809.132 Safari/537.36",
            'Cookie': Cookie,
        }

    def _http(self, url, headers, Obj=True, stream=False):
        response = requests.get(url, headers, proxies=self.proxies)
        # 这次大多都是处理json数据
        # 默认让她返回json对象，这样方便处理数据
        if Obj:
            return response.json()
        else:
            return response.content

    def update_author_name(self):
        '''
        @description: 根据用户id更新作者名字,保存URL的目录
        '''
        # 循环是为了防止未知错误发生，如代理断开
        while(self.author_name == ''):
            url = 'https://www.pixiv.net/users/{}'.format(self.author_id)
            # 构造http请求头
            headers = self.BaseHeader.copy()
            headers["Referer"] = 'https://www.pixiv.net/users/{}'.format(
                self.author_id)
            # 返回html页面数据
            data = self._http(url, headers, Obj=False).decode('utf-8')

            # RE刑法伺候
            name = re.findall('(?<=<title>)(.*?)(?=</title>)', data)[0]
            # 得到的是  三湊かおり - pixiv
            name = name.split(' ')[0]
            # 去除敏感符号防止命名文件时出错
            self.author_name = re.sub(r'[\/:*?"<>|]', '', name)

            # 防止作者名为空，影响极大
            if self.author_name == '':
                continue
            break
        # 更新URL保存目录
        self.url_path_name = './PixivURL/' + self.author_name + \
            '_' + self.author_id + '_urls.txt'
        print('作者名已经获取完毕： ' + self.author_name)

    def get_author_pic_url(self):
        '''
        @description: 根据用户id得到用户所有的作品id
        '''
        url = 'https://www.pixiv.net/ajax/user/{}/profile/all'.format(
            self.author_id)
        while(1):
            time.sleep(1)
            try:
                # http请求，返回json对象
                headers = self.BaseHeader.copy()
                headers["Referer"] = 'https://www.pixiv.net/users/{}/illustrations'.format(
                    self.author_id)

                # json对象=>字典对象=>字符串
                data = self._http(url, headers)

                # 获取所有的作品id
                ids = [i for i in data['body']['illusts']]
                return ids

            except Exception as e:
                print(str(e))
                print('获取作品所有id出错或者作者名字失败，正在重试.')
                continue

    def get_id_title(self, id):
        '''
        @description: 得到作品id对应的标题
        '''
        # 构造GET请求链接
        url = 'https://www.pixiv.net/ajax/user/{}/profile/illusts?ids[]={}&work_category=illust&is_first_page=1'.format(
            self.author_id, id)
        while(1):
            time.sleep(2)
            try:
                # http请求，返回json对象
                headers = self.BaseHeader.copy()
                headers["Referer"] = 'https://www.pixiv.net/users/{}/illustrations'.format(
                    self.author_id)
                # json对象=>字典对象=>字符串
                title = self._http(url, headers)[
                    'body']['works'][id]['illustTitle']
                # 过滤掉不允许的符号
                title = re.sub(r'[\/:*?"<>|]', '', title)
                return title
            except Exception as e:
                print(str(e))
                print(str(id)+' 标题获取错误！')
                continue

    def get_pic_url(self, id):
        '''
        @description: 得到每个作品id下图片url，并写入文件当中
        '''
        url = 'https://www.pixiv.net/ajax/illust/{}/pages'.format(id)
        while(1):
            print('正在处理: ' + str(id))
            time.sleep(1)
            try:
                # http请求，返回json对象
                headers = self.BaseHeader.copy()
                headers["Referer"] = 'https://www.pixiv.net/artworks/{}'.format(
                    id)
                data = self._http(url, headers)

                # 可能有多个图片,用json处理感觉不太方便,故用正则去匹配
                urls = re.findall("(?<='original': ').*?(?=')", str(data))

                # 抓取的url追加写入文件当中
                with open(self.url_path_name, 'a+') as f:
                    for u in urls:
                        f.seek(0)
                        if re.findall(u, f.read()):
                            print('此条链接已经写入，即将跳过.')
                        else:
                            f.write(u + '\n')
                    f.close()
                break
            except Exception as e:
                print(str(e))
                print('获取作品'+str(id)+'链接失败，正在重试.')
                continue

    def download_pic(self, url):
        '''
        @description: 下载给定url的作品图片
        '''
        # 以用户ID为文件夹名判断目录是否存在
        dirname = './PixivImage/' + self.author_name + '_' + self.author_id
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # 开始下载图片
        id = url.split('/')[-1].split('_')[0]
        title = str(self.get_id_title(id))
        filepath = './PixivImage/' + self.author_name + '_' + self.author_id + \
            '/' + title + '_' + url.split('/')[-1]

        # 判断图片是否存在
        if os.path.exists(filepath):
            print(title + '  文件已存在，即将跳过')
            return 0

        while(1):
            time.sleep(3)
            try:
                headers = self.BaseHeader.copy()
                headers["Referer"] = 'https://www.pixiv.net/artworks/{}'.format(
                    id)

                # tip:如若要保持stream=true，不能使用self._http函数
                # data = self._http(url, headers, Obj=False, stream=True)
                # stream=True 推迟下载响应
                with closing(requests.get(url, headers=headers, stream=True, proxies=self.proxies)) as response:
                    # 文件名构造不仅仅有作品ID还有作品标题，方便以后查阅
                    with open(filepath, 'wb+') as f:
                        print('正在下载===>>>>' + title + '_' +
                              url.split('/')[-1], end='')
                        f.write(response.content)
                        f.close()
                        print('===>>>>下载完成')
                break
            except Exception as e:
                print(str(e))
                print(title + '下载失败，正在重试.')
                pass

    def write_to_file(self):
        '''
        @description: 将得到的图片链接写入文本当中
        '''
        # 不敢直接遍历返回值，总是报错
        ids = self.get_author_pic_url()

        # 进程池同时处理
        pool = Pool(processes=20)
        pool.map(self.get_pic_url, ids)
        pool.close()
        pool.join()
        print(self.author_name + self.author_id +
              '旗下所有作品链接已经抓取完毕.保存在PixivURL目录下.')

    def download_from_file(self):
        '''
        @description: 从文本读取链接并下载
        '''
        with open(self.url_path_name, 'r') as f:
            # 进程池同时下载
            pool = Pool(processes=20)
            pool.map(self.download_pic, [line[:-1] for line in f.readlines()])
            pool.close()
            pool.join()

    def aoligei(self):
        # 这步十分重要
        self.update_author_name()
        self.write_to_file()
        self.download_from_file()


if __name__ == "__main__":
    # 设置参数
    cookie = "自个填"
    userid = '自个填'

    # 对每一个作者建立新类
    p = pixiv(userid, cookie)

    # 写了一天，喝杯茶，冷静
    p.aoligei()
