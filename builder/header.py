class Header:
    def __init__(self):
        self.headers = {}

    def set_header(self, key, value):
        self.headers[key] = value

    def set_header_from_dict(self, kv):
        for k, v in kv.items():
            self.set_header(k, v)

    def remove_header(self, key):
        if key in self.headers:
            del self.headers[key]

    def get(self):
        return self.headers

class HeaderBuilder:
    @staticmethod
    def build_common_header():
        common_header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "https://so.toutiao.com/search?dvpf=pc&source=pagination&keyword=%E5%8D%97%E4%BA%AC&pd=synthesis&action_type=pagination&page_num=1&search_id=202409031511249321F5AA49F1400A0BCC&from=search_tab&cur_tab_title=search_tab",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
            "sec-ch-ua": "\"Chromium\";v=\"128\", \"Not;A=Brand\";v=\"24\", \"Microsoft Edge\";v=\"128\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        header = Header()
        header.set_header_from_dict(common_header)
        return header

