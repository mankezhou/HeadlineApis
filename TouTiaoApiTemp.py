import base64
import json
import os
import random
import shutil
import time

import schedule
from loguru import logger

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from builder.auth import TouTiaoAuth
from builder.header import HeaderBuilder
from builder.params import Params
from common_utils.utils import validate_text
from utils.TouTiaoUtils import get_headers, generate_sign, trans_time, is_n_days_ago
logger.add("toutiao.log", rotation="10 MB", retention="10 days", compression="zip")

import re
ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
class TouTiaoApi:
    base_url = "https://so.toutiao.com"
    def getSearchInfo(self, keyword, page_num, auth):
        res = None
        success = True
        msg = '成功'
        try:
            api = "/search"
            headers = HeaderBuilder.build_common_header().get()
            cookies = auth.cookie
            params = {
                "dvpf": "pc",
                "source": "pagination",
                "keyword": keyword,
                "pd": "synthesis",
                "action_type": "pagination",
                "page_num": str(page_num),
                "search_id": "202409031511249321F5AA49F1400A0BCC",
                "from": "search_tab",
                "cur_tab_title": "search_tab"
            }
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies, params=params)
            res = response.text
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res

    def get_user_work_info(self, user_url, max_behot_time, auth):
        api = f"/api/pc/list/user/feed"
        headers = get_headers(user_url)
        token = user_url.split("/")[-2]
        params = Params()
        params.add_param("category", 'profile_all')
        params.add_param("token", token)
        params.add_param("max_behot_time", max_behot_time)
        params.add_param("entrance_gid", "")
        params.add_param("aid", '24')
        params.add_param("app_name", 'toutiao_web')
        params.with_ms_token()
        params.with_a_bogus()
        resp = requests.get(f'https://www.toutiao.com{api}', headers=headers, cookies=auth.cookie, params=params.get())
        return resp.json()

    def get_user_all_work(self, user_url, auth):
        max_behot_time = ''
        res = []
        while True:
            res_json = self.get_user_work_info(user_url, max_behot_time, auth)
            res.extend(res_json['data'])
            if not res_json['has_more']:
                break
            max_behot_time = res_json['next']['max_behot_time']
        return res

    def user_info(self, user_url, auth):
        # api = f"/api/pc/user/fans_stat"
        # url = f'https://www.toutiao.com{api}'
        # headers = get_headers(user_url)
        # token = user_url.split("/")[-2]
        # params = Params()
        # params.add_param("_signature", generate_sign(url))
        # data = {
        #     "token": token
        # }
        # params.with_a_bogus(data)
        # response = requests.post(url, headers=headers, cookies=auth.cookie, params=params.get(), data=data)
        # return response.json()
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": "https://www.toutiao.com/",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Microsoft Edge\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
        }
        url = "https://www.toutiao.com/c/user/token/MS4wLjABAAAA1pZNV0zb-MJvF3c5NASpaKnr8TtF_Gt_jwr0Qf3F_rk/"
        params = {
            "log_from": f"b24b98c824b3f_{time.time() * 1000}"
        }
        response = requests.get(url, headers=headers, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        user_profile = soup.find('div', attrs={"class": "profile-info-l"})
        avatar = user_profile.find('a', attrs={"class": "avatar"}).find('img')['src']
        detail = user_profile.find('div', attrs={"class": "detail"})
        nickname = detail.find('span', attrs={"class": "name"}).text
        user_desc = detail.find('span', attrs={"class": "user-desc"}).text
        relation = user_profile.find('div', attrs={"class": "relation-stat"}).find_all('span')
        user_digg_count = relation[0].text
        user_following = relation[1].text
        user_fans = relation[2].text
        res = {
            "data": {
                "avatar": avatar,
                "nickname": nickname,
                "user_desc": user_desc,
                "digg_count": user_digg_count,
                "following": user_following,
                "fans": user_fans
            }
        }
        return res

    def get_work_info(self, work_url, auth):
        headers = get_headers(work_url)
        response = requests.get(work_url, headers=headers, cookies=auth.cookie)
        res_text = response.text
        soup = BeautifulSoup(res_text, 'html.parser')
        script = soup.find_all('script', type="application/ld+json")
        info = script[0].string
        info = json.loads(info)

        images = []
        videos = []
        if 'article' in work_url:
            title = info['headline']
            content = soup.find('article').text
            images = info['image']
            videos_div = soup.find_all('div', attrs={'class': 'tt-video-box'})
            for video in videos_div:
                video_id = video['tt-videoid']
                video_url = self.get_video_url(video_id, auth)
                videos.append(video_url)
        else:
            title = info['name']
            content = info['description']
        res = {
            "title": ILLEGAL_CHARACTERS_RE.sub(r'', title),
            "content": ILLEGAL_CHARACTERS_RE.sub(r'', content),
            "images": images,
            "videos": videos
        }
        return res

    def get_video_url(self, video_id, auth):
        url = f"https://i.snssdk.com/video/urls/1/toutiao/mp4/{video_id}"
        headers = get_headers(url)
        params = {
            "callback": "tt__video__9n4f3t"
        }
        response = requests.get(url, headers=headers, cookies=auth.cookie, params=params)
        res_text = response.text
        res_text = res_text.replace("tt__video__9n4f3t(", "")[:-1]
        res_json = json.loads(res_text)
        video_url = res_json['data']['video_list']['video_1']['main_url']
        video_url = video_url.encode('utf-8')
        video_url = base64.b64decode(video_url)
        video_url = video_url.decode('utf-8')
        return video_url

    def get_one_user(self, user, auth_list, timesleep, recent_days):
        max_behot_time = ''
        res = []
        user_url = user['账号链接']
        auth = random.choice(auth_list)
        spider_user_info = self.user_info(user_url, auth)
        user_digg_count = spider_user_info['data']['digg_count']
        user_following = spider_user_info['data']['following']
        user_fans = spider_user_info['data']['fans']
        user_id = user_url.split("/")[-2]
        break_flag = True
        while break_flag:
            auth = random.choice(auth_list)
            res_json = self.get_user_work_info(user_url, max_behot_time, auth)
            time.sleep(timesleep)
            data = res_json['data']
            for work in data:
                try:
                    work_id = work['id']
                    work_info = dict()
                    work_info.update(user)
                    if 'video' in work:
                        auth = random.choice(auth_list)
                        work_url = f"https://www.toutiao.com/video/{work_id}/"
                        work_info_detail = self.get_work_info(work_url, auth)
                        work_info.update(work_info_detail)
                        video_id = work['video']['play_addr']['uri']
                        video_url = self.get_video_url(video_id, auth)
                        videos = [video_url]
                        work_info['videos'] = videos
                        like_count = work['itemCell']['itemCounter']['diggCount']
                        comment_count = work['itemCell']['itemCounter']['commentCount']
                        nickname = work['user']['info']['name']
                        user_desc = work['user']['info']['desc']
                        user_avatar = work['user']['info']['avatar_url']
                    elif 'toutiao.com/w/' in work['share_url'] or (
                            'comment_base' in work and 'toutiao.com/w/' in work['comment_base']['share']['share_url']):
                        work_url = work['share_url']
                        if work_url == '':
                            continue
                        work_info['title'] = work['title']
                        res_text_temp = requests.get(work_url, headers=get_headers(work_url), cookies=auth.cookie).text
                        soup = BeautifulSoup(res_text_temp, 'html.parser')
                        content = soup.find('article').text
                        work_info['content'] = ILLEGAL_CHARACTERS_RE.sub(r'', content)
                        images = []
                        images_div = soup.find_all('div', attrs={'class': 'image-list'})
                        if images_div and len(images_div) > 0:
                            images_div = images_div[0].find_all('img')
                            for image in images_div:
                                src = image.attrs['src']
                                images.append(f'https:{src}'.replace('amp;', ''))
                        work_info['images'] = images
                        videos = []
                        work_info['videos'] = videos
                        like_count = work['digg_count']
                        comment_count = work['comment_count']
                        nickname = work['user']['name']
                        user_desc = work['user']['desc']
                        user_avatar = work['user']['avatar_url']
                    else:
                        work_url = f"https://www.toutiao.com/article/{work_id}/"
                        work_info_detail = self.get_work_info(work_url, auth)
                        work_info.update(work_info_detail)
                        like_count = work['like_count']
                        comment_count = work['comment_count']
                        nickname = work['user_info']['name']
                        user_desc = work['user_info']['description']
                        user_avatar = work['user_info']['avatar_url']

                    time.sleep(timesleep)
                    try:
                        read_count = work['itemCell']['itemCounter']['readCount']
                    except:
                        read_count = 0
                    try:
                        showCount = work['itemCell']['itemCounter']['showCount']
                    except:
                        showCount = 0
                    try:
                        shareCount = work['itemCell']['itemCounter']['shareCount']
                    except:
                        shareCount = 0
                    publish_time = work['publish_time']
                    publish_time = trans_time(publish_time)
                    work_info['work_url'] = work_url
                    work_info['like_count'] = like_count
                    work_info['comment_count'] = comment_count
                    work_info['read_count'] = read_count
                    work_info['show_count'] = showCount
                    work_info['share_count'] = shareCount
                    work_info['publish_time'] = publish_time
                    user_info = {
                        "user_url": user_url,
                        "user_id": all_toutiao_dict[user_id] if user_id in all_toutiao_dict else user_id,
                        "nickname": nickname,
                        "user_desc": ILLEGAL_CHARACTERS_RE.sub(r'', user_desc),
                        "user_avatar": user_avatar,
                        "user_digg_count": user_digg_count,
                        "user_following": user_following,
                        "user_fans": user_fans
                    }
                    work_info.update(user_info)

                    if not recent_days == -1:
                        if not is_n_days_ago(work_info['publish_time'], recent_days):
                            if 'is_stick' in work and work['is_stick']:
                                continue
                            break_flag = False
                            break

                    res.append(work_info)
                    logger.info(f'爬取作品 {work_url} 信息成功')
                    logger.info(f'{work_info}')
                except Exception as e:
                    logger.error(f'爬取作品 {work} 信息失败: {e}')
            if not res_json['has_more']:
                break
            max_behot_time = res_json['next']['max_behot_time']
        for item in res:
            item['作品数量'] = len(res)
        if len(res) == 0:
            one_item = user.copy()
            one_item_other = {
                "title": "该用户没有发帖",
                "content": "",
                "images": [],
                "videos": [],
                "work_url": "",
                "like_count": 0,
                "comment_count": 0,
                "read_count": 0,
                "show_count": 0,
                "share_count": 0,
                "publish_time": "",
                "user_url": user_url,
                "user_id": all_toutiao_dict[user_id] if user_id in all_toutiao_dict else user_id,
                "nickname": spider_user_info['data']['nickname'],
                "user_desc": spider_user_info['data']['user_desc'],
                "user_avatar": spider_user_info['data']['avatar'],
                "user_digg_count": user_digg_count,
                "user_following": user_following,
                "user_fans": user_fans,
                "作品数量": 0
            }
            one_item.update(one_item_other)
            res.append(one_item)
        return res

    def save_to_excel(self, save_path, res):
        df = pd.DataFrame(res)
        df.to_excel(save_path, index=True)

    def all_all_users(self, path):
        df = pd.read_excel(path)
        datas = df.to_numpy().tolist()
        users = []
        for data in datas:
            url = str(data[5])
            if 'www.toutiao.com' in url:
                users.append({
                    '账号编号': str(data[0]),
                    '序号': str(data[1]),
                    '平台': str(data[2]),
                    '赛道（一类）': data[3],
                    '赛道（二类）': data[4],
                    '账号链接': url
                })
        return users

    def main(self, spider_files, auth_list, timesleep, recent_days):
        for spider_index, file_name in enumerate(spider_files):
            logger.info(f'开始爬取第 {spider_index} 项目 {file_name} 的所有用户的所有发帖信息')
            # simple_file_name = validate_text(file_name)
            simple_file_name = '.'.join(file_name.split('.')[:-1])
            work_dir = os.path.abspath(os.path.dirname(__file__))
            base_path = os.path.abspath(os.path.join(work_dir, '..'))
            save_base_path = os.path.abspath(os.path.join(base_path, 'data', 'toutiao', simple_file_name))
            if not os.path.exists(save_base_path):
                os.makedirs(save_base_path)
            spider_file_path = os.path.abspath(os.path.join(base_path, 'input', file_name))
            users = self.all_all_users(spider_file_path)
            for index, user in enumerate(users):
                try:
                    user_url = user['账号链接']
                    user_id = user_url.split("/")[-2]
                    save_path = f'{save_base_path}/{user_id}.xlsx'
                    if os.path.exists(save_path):
                        logger.info(f'用户 {user_url} 的所有发帖信息已经爬取过')
                        continue
                    logger.info(f'-----------------------------------')
                    logger.info(f'开始爬取第 {spider_index} 项目 {simple_file_name} 的第{index + 1}个用户 {user_url} 的所有发帖信息')
                    res = self.get_one_user(user, auth_list, timesleep, recent_days)
                    self.save_to_excel(save_path, res)
                    logger.info(f'第 {spider_index} 项目 {simple_file_name} 剩余用户数: {len(users) - index - 1}')
                except Exception as e:
                    logger.error(f'爬取用户 {user} 失败: {e}')
            self.combine(save_base_path)

    def combine(self, save_base_path):
        if os.path.exists(f'{save_base_path}/all.xlsx'):
            os.remove(f'{save_base_path}/all.xlsx')
        all_excel = os.listdir(save_base_path)
        all_res = []
        for excel in all_excel:
            if excel.endswith('.xlsx'):
                df = pd.read_excel(f'{save_base_path}/{excel}', dtype=str).iloc[:, 1:]
                res = df.to_numpy().tolist()
                all_res.extend(res)

        columns = ['账号编号', '序号', '平台', '赛道（一类）', '赛道（二类）', '账号链接', '标题', '内容', '图片', '视频', '作品链接', '点赞数', '评论数', '阅读数', '展现数', '分享数', '发布时间', '用户主页', '用户ID', '用户昵称', '用户描述', '用户头像', '用户点赞数', '用户关注数', '用户粉丝数', '用户作品数量']
        df = pd.DataFrame(all_res, columns=columns)
        df.to_excel(f'{save_base_path}/all.xlsx', index=True)

def job():
    touTiaoApi = TouTiaoApi()
    work_dir = os.path.abspath(os.path.dirname(__file__))
    env_path = os.path.join(work_dir, '..', 'env.yaml')
    env_path = os.path.abspath(env_path)
    with open(env_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    toutiao_config = config['platform']['toutiao']
    timesleep = toutiao_config['timesleep']
    recent_days = toutiao_config['recent_days']
    cookies_strs = toutiao_config['cookies_strs']
    spider_files = toutiao_config['spider_files']
    auth_list = []
    for cookies_str in cookies_strs:
        auth_ = TouTiaoAuth()
        auth_.perepare_auth(cookies_str)
        auth_list.append(auth_)
    touTiaoApi.main(spider_files, auth_list, timesleep, recent_days)

def schedule_job():
    work_dir = os.path.abspath(os.path.dirname(__file__))
    base_path = os.path.abspath(os.path.join(work_dir, '..'))
    save_base_path = os.path.abspath(os.path.join(base_path, 'data', 'toutiao'))
    logger.info(f'清理 {save_base_path} 下的所有文件和文件夹')
    # 清理save_base_path下的所有文件和文件夹
    for filename in os.listdir(save_base_path):
        file_path = os.path.join(save_base_path, filename)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
    job()
    job()


othor_info_excel_path = os.path.abspath(os.path.join((os.path.dirname(__file__)), 'static', '今日头条账号链接.xlsx'))
all_toutiao_users = pd.read_excel(othor_info_excel_path).to_numpy().tolist()
all_toutiao_dict = dict()
for user in all_toutiao_users:
    all_toutiao_dict[user[6].split("/")[-2]] = user[4].replace('编号', '')



if __name__ == '__main__':
    # job()
    schedule_job()

    # schedule.every().monday.at("00:05").do(schedule_job)
    # schedule.every().tuesday.at("00:05").do(schedule_job)
    # schedule.every().wednesday.at("00:05").do(schedule_job)
    # schedule.every().thursday.at("00:05").do(schedule_job)
    # schedule.every().friday.at("00:05").do(schedule_job)
    #
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)