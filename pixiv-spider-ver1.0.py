#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Author:  Zyue
# Time: 2020.01.30

# requeset.get的cookie设置是 'Cookie'！！！！
# 靠调试好久 我一直填的是Cookies！！！
# 变量名一定要填对

# 使用方法：
# 注意填 user_id 和 Cookie
# 代理地址自己改吧
# 已经用类改写ver2.0，这块不管了

import requests
import os
from lxml import etree
import re
from contextlib import closing
import urllib
from multiprocessing import Pool
import time

proxies = {"http": "http://127.0.0.1:10809",
           "https": "http://127.0.0.1:10809"}
user_id = '自己填'


def get_author(user_id):
    '''
    @description: 根据作者id得到作者名字
    '''
    url = 'https://www.pixiv.net/ajax/user/{}/profile/all'.format(user_id)
    while(1):
        time.sleep(1)
        try:
            with closing(requests.get(url, headers=get_headers('https://www.pixiv.net/'), proxies=proxies)) as response:
                # json对象=>字典对象=>字符串
                data = response.json()
                # 正则处理作者名字
                author = data['body']['pickup'][0]['userName']
                author = re.sub(r'[\/:*?"<>|]', '', author)
                return author
        except Exception as e:
            print(str(e))
            print('获取作者名字失败，正在重试.')
            continue


def get_headers(url):
    headers = {
        'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/76.0.3809.132 Safari/537.36",
        'Referer': url,
        'Cookie': '填自己的cookie'
    }
    return headers


def get_user_all_pic_id(user_id):
    '''
    @description: 根据用户id得到用户所有的作品id
    '''
    url = 'https://www.pixiv.net/ajax/user/{}/profile/all'.format(user_id)
    while(1):
        time.sleep(1)
        try:
            with closing(requests.get(url, headers=get_headers('https://www.pixiv.net/users/{}/illustrations'.format(user_id)), proxies=proxies)) as response:
                # json对象=>字典对象=>字符串
                data = response.json()
                ids = [i for i in data['body']['illusts']]
                return ids
        except Exception as e:
            print(str(e))
            print('获取所有用户下作品id失败，正在重试.')
            continue


def get_id_title(id):
    '''
    @description: 得到作品id对应的标题
    '''
    # 构造GET请求链接
    url = 'https://www.pixiv.net/ajax/user/{}/profile/illusts?ids[]={}&work_category=illust&is_first_page=1'.format(
        user_id, id)
    while(1):
        time.sleep(2)
        try:
            with closing(requests.get(url, headers=get_headers('https://www.pixiv.net/users/{}/illustrations'.format(user_id)), proxies=proxies)) as response:
                # 处理返回的json数据
                data = response.json()
                title = data['body']['works'][id]['illustTitle']
                # 过滤掉不允许的符号
                title = re.sub(r'[\/:*?"<>|]', '', title)
                return title
        except Exception as e:
            print(str(e))
            print(str(id)+' 标题获取错误！')
            continue


def get_pic_url(id):
    '''
    @description: 得到每个作品id下图片url，并写入文件当中
    '''
    epi_url = 'https://www.pixiv.net/ajax/illust/{}/pages'.format(id)
    author = get_author(user_id)

    while(1):
        print('正在处理: ' + str(id))
        time.sleep(1)
        try:
            with closing(requests.get(epi_url, headers=get_headers('https://www.pixiv.net/artworks/{}'.format(id)), proxies=proxies)) as response:
                # 可能有多个图片，用json处理感觉不太方便
                # 故用正则去匹配
                data = str(response.json())
                urls = re.findall("(?<='original': ').*?(?=')", data)
                # 抓取的url追加写入文件当中
                with open('./' + author + '_' + user_id + '_urls.txt', 'a') as f:
                    for u in urls:
                        f.write(u + '\n')
                    f.close()
                break
        except Exception as e:
            print(str(e))
            print('获取作品'+str(id)+'链接失败，重试.')
            continue


def download_pic(url):
    '''
    @description: 下载作品图片
    '''
    author = get_author(user_id)
    # 以用户ID为文件夹名判断目录是否存在，
    if os.path.exists('./PixivImage/' + author + '_' + user_id) == 0:
        os.makedirs('./PixivImage/' + author + '_' + user_id)

    # 开始下载图片
    id = url.split('/')[-1].split('_')[0]
    title = str(get_id_title(id))
    filepath = './PixivImage/' + author + '_' + user_id + \
        '/' + title + '_' + url.split('/')[-1]

    # 判断图片是否存在
    if os.path.exists(filepath):
        print(title + '  文件已存在，即将跳过')
        return 0

    while(1):
        time.sleep(3)
        try:
            # stream=True 推迟下载响应
            with closing(requests.get(url, headers=get_headers('https://www.pixiv.net/artworks/{}'.format(id)), stream=True,
                                      proxies=proxies)) as response:
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


def write_to_file():
    '''
    @description: 将得到的图片链接写入文本当中
    @param {type}
    @return:
    '''
    # 单线程方法
    # 不敢直接遍历返回值，总是报错
    ids = get_user_all_pic_id(user_id)
    # for id in ids:
    #     get_pic_url(id)

    # 多线程同时处理5个
    pool = Pool(processes=20)
    pool.map(get_pic_url, ids)
    pool.close()
    pool.join()
    print(user_id + '链接已经抓取完毕')


def download_from_file():
    author = get_author(user_id)
    with open('./' + author + '_' + user_id + '_urls.txt', 'r') as f:
        # 多线程同时下载5个
        pool = Pool(processes=20)
        pool.map(download_pic, [line[:-1] for line in f.readlines()])
        pool.close()
        pool.join()


if __name__ == "__main__":
    write_to_file()
    download_from_file()
