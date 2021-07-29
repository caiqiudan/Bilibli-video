import requests
from parsel import Selector
import os
from time import time, sleep
from winreg  import OpenKey, QueryValueEx, HKEY_CURRENT_USER # 获取当前桌面路径

'''
Author：xaufe Applied statistics Caiqiudan
'''

class GetBv():
    def __init__(self, bvid, page=1):
        '''
        bvid:视频号 eg:BV1hE411N7q2，str
        page: P几的视频，默认为1 int
        '''
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1', 'Referer': 'https://www.bilibili.com', } # 表头
        self.bvid = bvid    # bv号
        self.page = page    # 页数
        self.pg_dic, self.video_name, self.all_page, self.cids = GetBv.get_name_pages(self)  # 视频名称表单、视频名称、总视频数
        
    # 获取视频名称表单并创建存放视频的文件夹
    def get_name_pages(self):
        # 获取名称表单
        url = f'https://www.bilibili.com/video/{self.bvid}'
        r_ng = requests.get(url)
        selector = Selector(r_ng.text)

        video_message = selector.xpath('/html/head/script[6]/text()').getall()[0]
        false = False; true = True; null = None
        video_message = eval(video_message[video_message.index('{'):-video_message[::-1].index(';}')-1])

        all_page = video_message['videoData']['videos']  # 总页数/视频数
        page_name_dic = {}  # 页数对应的名称
        for x in video_message['videoData']['pages']:
            page_name_dic[x['page']] = x['part']

        video_name = video_message['videoData']['title'] # 视频总标题
        for i in ['*', '"', '/', ':', '?', '\\', '|', '<', '>']:    # 文件名不能含有*?/\...
            video_name = video_name.replace(i, ' ')
        # cids--用来获取字幕的网址
        cids = [i['cid'] for i in video_message['videoData']['pages']]
        return page_name_dic, video_name, all_page, cids
    
    # 获取视频网址和cid(cid用来获取弹幕网址)
    def get_video_audio_urls(self):
        url = f'https://www.bilibili.com/video/{self.bvid}?p={self.page}'
        r = requests.get(url)
        selector = Selector(text=r.text)
        urlData = selector.xpath('/html/head/script/text()').getall()
        video_audio = urlData[3]       # 视频和音频
        subtitles = urlData[4]         # 字幕
        null = None; false = False; true = True       # 防止eval报错未定义
        # 视频链接
        video_dic = eval(video_audio[video_audio.index('{'):])['data']['dash']['video']  # 找到{}才能loads
        video_url = video_dic[0]['baseUrl']
        # 音频链接
        audio_dic = eval(video_audio[video_audio.index('{'):])['data']['dash']['audio']
        audio_url = audio_dic[0]['baseUrl']
        return video_url, audio_url # , sub_url_dic

    # 下载video.m4s和audio.m4s格式的音频和视频
    def get_mp4(self):
        # bv_name: 视频名称
        bv_name = f'P{self.page} '+ self.pg_dic[self.page]
        for i in ['*', '"', '/', ':', '?', '\\', '|', '<', '>']:    # 文件名不能含有*?/\...
            bv_name = bv_name.replace(i, ' ')
        self.path = f'{self.file_path}/{bv_name}'  # 视频路径
        if os.path.exists(f'{self.path}.mp4'):  # 若已存在该视频则跳出函数
            print(f'已存在第{self.page}P视频——{bv_name}.mp4')
            GetBv.get_subtitle(self)
            return
        video_url, audio_url = GetBv.get_video_audio_urls(self)
        va_dic = {f'{self.path}_video.m4s':video_url, f'{self.path}_audio.m4s':audio_url}
        video_path, audio_path = list(va_dic.keys())
        # 遍历，依次下载视频和音频
        for va_path in va_dic.keys():
            start = time()
            size = 0
            # stream参数设置成True时，它不会立即开始下载，当你使用iter_content或iter_lines遍历内容或访问内容属性时才开始下载
            va_r = requests.get(va_dic[va_path], headers=self.headers, stream=True)
            chunk_size = 1024  # 每次块大小为1024
            content_size = int(va_r.headers['content-length'])  # 返回的response的headers中获取文件大小信息
            print(f"下载第{page}P，共{len(page_list)}P"); print(f"{va_path[len(self.file_path)+1:]},文件大小：{format(content_size / chunk_size / 1024, '.2f')}MB")
            with open(va_path, 'wb') as f:
                for data in va_r.iter_content(chunk_size=chunk_size):  # 每次只获取一个chunk_size大小
                    f.write(data)  # 每次只写入data大小
                    size = len(data) + size
                    # 'r'每次重新从开始输出，end = ""是不换行
                    print('\r' + "进度：" + int(size / content_size * 30) * "█" + f" 【{format(size / chunk_size / 1024, '.2f')}MB】 【{format(size / content_size, '.2%')}】", end="")
            end = time()
            print("   总耗时:%.2f秒" % (end - start))

        # 合并视频
        order = 'ffmpeg -i "'+video_path+'" -i "'+audio_path+'" -codec copy "'+f'{self.path}.mp4'+'" -loglevel quiet'  # 路径加引号是为了解决路径不能包含空格 . 的问题
        os.system(order)
        # 删除原来的音频+视频.m4s文件
        os.remove(video_path); os.remove(audio_path); print(f'合并为{bv_name}.mp4')
        # 下载字幕
        GetBv.get_subtitle(self)
        
    def s2hms(x):      # 把秒转为时分秒
        m, s = divmod(x, 60)
        h, m = divmod(m, 60)
        hms = "%02d:%02d:%s"%(h,m,str('%.3f'%s).zfill(6))
        hms = hms.replace('.',',')       # 把小数点改为逗号
        return hms
    
    def get_subtitle(self):
        # 获取字幕网址
        cid_url = f'https://api.bilibili.com/x/player/v2?cid={self.cids[self.page-1]}&bvid={self.bvid}'  # 只需要cid和bvid
        cid_r = requests.get(cid_url)
        sub_list = cid_r.json()['data']['subtitle']['subtitles']
        # 遍历每份字幕网址
        for sub in sub_list:
            r_sub = requests.get('https:'+sub['subtitle_url'])
            sub_content = r_sub.json()['body']
            # 判断该字幕是否存在
            if not os.path.exists('%s_%s.srt'%(self.path, sub['lan_doc'])):   # 如果不存在该字幕文件则下载该字幕文件
                # 写入srt文件
                with open('%s_%s.srt'%(self.path, sub['lan_doc']), 'w', encoding='utf-8') as f:
                    write_content = [str(n+1)+'\n' + GetBv.s2hms(i['from'])+' --> '+GetBv.s2hms(i['to'])+'\n' + i['content']+'\n\n' for n,i in enumerate(sub_content)] # 序号+开始-->结束+内容
                    f.writelines(write_content)
                print('下载 p%s %s字幕'%(self.page, sub['lan_doc']))
            else:
                print('已存在p%s %s字幕'%(self.page, sub['lan_doc']))

if __name__ == '__main__':
    print('提示：在执行此程序之前请安装好ffmpeg并配置环境变量')
    bvid = input('请输入视频的BV号: ')
    while True:
        while True:   # 若网络不行或格式有误则循环
            try:
                getBv = GetBv(bvid)
                break
            except requests.exceptions.ConnectionError:
                print('请检查网络的连通性！')
                bvid = input('请确保网络连通，并重新输入视频的BV号: ')
            except (IndexError):
                print('输入的视频号有误，请在该视频链接找到如格式为 BV1C5411H7dz的BV号并输入.')
                bvid = input('请输入视频的BV号: ')
        print(f'----------  {getBv.video_name}  ----------')  # 视频名称
        
        # 视频路径
        while True:
            my_path = input(f'\n请输入存放视频的文件夹路径（直接回车即默认在当前桌面的{getBv.video_name}文件夹下存放视频):')
            if my_path == '123':    # 我的快捷路径
                my_path = 'D:\\User\\Videos'
                getBv.file_path = os.path.join(my_path, getBv.video_name)
                break
            elif my_path == '':     # 默认路径为桌面
                key = OpenKey(HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
                my_path = QueryValueEx(key, 'Desktop')[0]
                getBv.file_path = os.path.join(my_path, getBv.video_name)
                break
            elif os.path.exists(my_path):
                getBv.file_path = os.path.join(my_path, getBv.video_name)
                break
            else:
                print('输入路径有误，请检查路径！')
                          
        if not os.path.exists(getBv.file_path):  # 判断是否存在该文件夹，不存在则创建
            os.mkdir(getBv.file_path)
        print(f'视频将存放在 "{getBv.file_path}"路径下')
        
        # 视频范围
        while True:    # 如果输入格式有误则循环
            page_range = input('\n下载视频数范围(空格隔开)(直接回车即下载全部视频)：')
            if page_range == '':
                min_page = 1
                max_page = getBv.all_page  # 获取最大页数
                break
            else:
                try:
                    min_page = int(page_range.split()[0])
                    max_page = int(page_range.split()[-1])
                    break
                except:
                    print('输入格式有误(提示: 如下载第1P到第15P的视频，输入：1 15，如只下载1P的视频，输入：1)：')
        page_list = range(min_page, max_page + 1)

        print(f'\n开始爬取第{min_page}-{max_page}P的视频...')
        for page in page_list:
            getBv.page = page
            getBv.get_mp4()
            # 爬取对应的字幕
        print(f'\n爬取完成，请在"{getBv.file_path}"路径下查看')

        bvid = input('请输入视频的BV号（或按回车键退出）：')
        if not bvid:   # 如果按回车，则退出循环
            print('               ii.                                         ;9ABH,          \n' +
'              SA391,                                    .r9GG35&G          \n' +
'              &#ii13Gh;                               i3X31i;:,rB1         \n' +
'              iMs,:,i5895,                         .5G91:,:;:s1:8A         \n' +
'               33::::,,;5G5,                     ,58Si,,:::,sHX;iH1        \n' +
'                Sr.,:;rs13BBX35hh11511h5Shhh5S3GAXS:.,,::,,1AG3i,GG        \n' +
'                .G51S511sr;;iiiishS8G89Shsrrsh59S;.,,,,,..5A85Si,h8        \n' +
'               :SB9s:,............................,,,.,,,SASh53h,1G.       \n' +
'            .r18S;..,,,,,,,,,,,,,,,,,,,,,,,,,,,,,....,,.1H315199,rX,       \n' +
'          ;S89s,..,,,,,,,,,,,,,,,,,,,,,,,....,,.......,,,;r1ShS8,;Xi       \n' +
'        i55s:.........,,,,,,,,,,,,,,,,.,,,......,.....,,....r9&5.:X1       \n' +
'       59;.....,.     .,,,,,,,,,,,...        .............,..:1;.:&s       \n' +
'      s8,..;53S5S3s.   .,,,,,,,.,..      i15S5h1:.........,,,..,,:99       \n' +
'      93.:39s:rSGB@A;  ..,,,,.....    .SG3hhh9G&BGi..,,,,,,,,,,,,.,83      \n' +
'      G5.G8  9#@@@@@X. .,,,,,,.....  iA9,.S&B###@@Mr...,,,,,,,,..,.;Xh     \n' +
'      Gs.X8 S@@@@@@@B:..,,,,,,,,,,. rA1 ,A@@@@@@@@@H:........,,,,,,.iX:    \n' +
'     ;9. ,8A#@@@@@@#5,.,,,,,,,,,... 9A. 8@@@@@@@@@@M;    ....,,,,,,,,S8    \n' +
'     X3    iS8XAHH8s.,,,,,,,,,,...,..58hH@@@@@@@@@Hs       ...,,,,,,,:Gs   \n' +
'    r8,        ,,,...,,,,,,,,,,.....  ,h8XABMMHX3r.          .,,,,,,,.rX:  \n' +
'   :9, .    .:,..,:;;;::,.,,,,,..          .,,.               ..,,,,,,.59  \n' +
'  .Si      ,:.i8HBMMMMMB&5,....                    .            .,,,,,.sMr\n' +
'  SS       :: h@@@@@@@@@@#; .                     ...  .         ..,,,,iM5\n' +
'  91  .    ;:.,1&@@@@@@MXs.                            .          .,,:,:&S\n' +
'  hS ....  .:;,,,i3MMS1;..,..... .  .     ...                     ..,:,.99\n' +
'  ,8; ..... .,:,..,8Ms:;,,,...                                     .,::.83\n' +
'   s&: ....  .sS553B@@HX3s;,.    .,;13h.                            .:::&1\n' +
'    SXr  .  ...;s3G99XA&X88Shss11155hi.                             ,;:h&,\n' +
'     iH8:  . ..   ,;iiii;,::,,,,,.                                 .;irHA  \n' +
'      ,8X5;   .     .......                                       ,;iihS8Gi\n' +
'         1831,                                                 .,;irrrrrs&@\n' +
'           ;5A8r.                                            .:;iiiiirrss1H\n' +
'             :X@H3s.......                                .,:;iii;iiiiirsrh\n' +
'              r#h:;,...,,.. .,,:;;;;;:::,...              .:;;;;;;iiiirrss1\n' +
'             ,M8 ..,....,.....,,::::::,,...         .     .,;;;iiiiiirss11h\n' +
'             8B;.,,,,,,,.,.....          .           ..   .:;;;;iirrsss111h\n' +
'            i@5,:::,,,,,,,,.... .                   . .:::;;;;;irrrss111111\n' +
'            9Bi,:,,,,......                        ..r91;;;;;iirrsss1ss1111 \n'+
'使用愉快~')
            sleep(0.5)
            break