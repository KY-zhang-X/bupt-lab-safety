# coding=utf-8

import traceback
from typing import Tuple
import requests
from bs4 import BeautifulSoup
import json
import itertools

class LabSafe(object):

    # 实验室安全教育与考试系统IP地址
    host = '10.3.240.204'

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'

    def login(self, username: str, password: str):
        '''
        使用学号和密码登录
        '''
        data = {
            'j_username': username,
            'j_password': password,
        }
        res = self.session.post(url=f'http://{self.host}/j_spring_security_check', data=data)
        return res

    def run(self, knowid, deptId):
        '''
        自动获取knowid和deptId对应题库的题目和答案，然后输出到文件中
        '''
        db_list = []
        try:
            # 获取第一个问题
            res = self.session.get(url=f'http://{self.host}/exam/studenttest/studentTestAction.do?ms=gotoStudyThemePass&knowid={knowid}&deptId={deptId}')
            page = 0
            max_page = 1
            while page < max_page:
                # 解析问题页面
                question_url, options_dict = self.parse_question(res.text)
                input_name = self.parse_input_name(res.text)
                question_type = ''
                question_text = ''
                answer = ''
                inputs_dict = self.parse_hidden_inputs(res.text)
                page = int(inputs_dict['pageNum'])
                max_page = int(inputs_dict['maxPage'])
                # 根据不同题目类型确定不同的做法
                if input_name == 'answerradio': # 单选题依次遍历选项，进行提交
                    question_type = '单选题'
                    for option in options_dict.keys():
                        inputs_dict['answerradio'] = option
                        res = self.session.post(url=f'http://{self.host}/exam/studenttest/studentTestAction.do?ms=gotoStudyThemePassAnswer', data=inputs_dict)
                        result, question_text= self.parse_answer(res.text)
                        if result:
                            answer = list(option)
                            inputs_dict = self.parse_hidden_inputs(res.text)
                            break
                elif input_name == 'answercheckbox': # 多选题依次遍历选项的组合，进行提交（从选较多选项的情况开始遍历）
                    question_type = '多选题'
                    opt_list = options_dict.keys() # 所有可选的选项构成的list
                    for i in range(len(opt_list), 0, -1): # 生成i个选项的组合
                        for opts in itertools.combinations(opt_list, i):
                            inputs_dict['answercheckbox'] = list(opts)
                            res = self.session.post(url=f'http://{self.host}/exam/studenttest/studentTestAction.do?ms=gotoStudyThemePassAnswer', data=inputs_dict)
                            # print(res.text)
                            result, question_text= self.parse_answer(res.text)
                            if result:
                                answer = opts
                                inputs_dict = self.parse_hidden_inputs(res.text)
                                break
                        else:
                            continue
                        break # 连续跳出多层循环
                else:
                    raise Exception('未知的题目类型')
                db_list.append({'qtext':question_text, 'qurl':question_url, 'qtype': question_type, 'opts':options_dict, 'ans':answer})
                print(f"{page}: {question_text}")
                inputs_dict['pageNum'] = str(page+1)
                res = self.session.post(url=f'http://{self.host}/exam/studenttest/studentTestAction.do?ms=gotoStudyThemePass', data=inputs_dict)
        except Exception as e:
            traceback.print_exc()
        # 以json格式保存得到的题目
        with open(f'./{knowid}_{deptId}.json', 'w', encoding='utf-8') as file:
            json.dump(db_list, file, indent=4, ensure_ascii=False)

    def parse_question(self, html) -> Tuple[str, dict]:
        '''
        解析问题图片url和选项列表
        '''
        soup = BeautifulSoup(html, 'html.parser')
        question_url = soup.select_one('img[src]')['src']
        input_tags_list = soup.select('input[name^="answer"][value]')
        options_dict = {}
        for input_tag in input_tags_list:
            option_tag = input_tag.parent
            option_text = option_tag.get_text().strip().replace('\u00a0','')
            option_value = input_tag['value']
            options_dict[option_value] = option_text
        return (question_url, options_dict)
    
    def parse_input_name(self, html) -> str:
        '''
        解析选项输入方式，用于判断题目类型
        '''
        soup = BeautifulSoup(html, 'html.parser')
        input = soup.select_one('input[name^="answer"]')
        return input['name']


    def parse_answer(self, html) -> Tuple[bool, str]:
        '''
        解析答案是否正确并获得题目文本
        '''
        soup = BeautifulSoup(html, 'html.parser')
        color = soup.select_one('font[color]')['color']
        question_text = soup.select_one('td[style][colspan]').get_text().strip()
        if color == 'green':
            return (True, question_text)
        else:
            return (False, question_text)

    def parse_hidden_inputs(self, html) -> dict:
        '''
        解析得到题库状态信息，用于进入下一题
        '''
        soup = BeautifulSoup(html, 'html.parser')
        inputs = soup.select('input[type="hidden"]')
        inputs_dict = dict([(input['name'], input['value']) for input in inputs])
        return inputs_dict

if __name__ == '__main__':
    # 使用学号和密码登录
    username = '2022xxxxxx'
    password = 'xxxxxxxxxx'
    lab = LabSafe()
    lab.login(username, password)
    # 从实验室考试系统的“自学”页面得到的id
    knowid = [446606,446628,446661,446683,446634,446648,446345,446622,446659,446631,446652]
    deptId = [450536,450564,450568]
    # 先遍历知识点的题库
    for i in knowid:
        lab.run(i, 0)
    # 再遍历学院的题库
    for i in deptId:
        lab.run(-1, i)
