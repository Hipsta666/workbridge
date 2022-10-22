from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import requests
import time
import string
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from threading import *
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import SnowballStemmer
from sklearn.feature_extraction.text import CountVectorizer
from scipy import spatial
from string import digits

# Получение токена резюме - перейти по адресу https://hh.ru/oauth/authorize?response_type=code&client_id=RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70
# # Resume
# response = requests.post('https://hh.ru/oauth/token', data={'client_secret':'SEJEQ0GVK6I7PLJCHC7VIFFIMIDLPM1KECK4UP315NU3I7MLKFCVK84SQEDLGEC0', 'client_id': 'RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70', 'grant_type':'authorization_code', 'code': 'UHVU14H9E26V5AL5256EN8CDMJ94SLEUR7LFGNB8HJ135E5RTB50V0PEUSBPUH58'})
# print(response.text)

# # Vacancies
# response = requests.post('https://hh.ru/oauth/token', data={'client_secret':'SEJEQ0GVK6I7PLJCHC7VIFFIMIDLPM1KECK4UP315NU3I7MLKFCVK84SQEDLGEC0', 'client_id': 'RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70', 'grant_type':'client_credentials'})
# print(response.text)

with open("/Users/hipsta/Desktop/MyDevelop/LaMa-Assistant/server/dict.json", "r",  encoding="utf-8") as f:
        dictionary = json.load(f)


stop_words = stopwords.words('russian')
stemmer = SnowballStemmer(language='russian')
punct = string.punctuation.replace("#", "") + '—' + '”' + '“' + '``' + '«' + '»' + '•' + '/' + ' '
headersForVacancy = {'Authorization': 'Bearer UU127MI5EQ2PCQ9KKLEC2IIFSU3SFO7146N85GSLFPPCV6HVAEOLAALHKNDB2CVA'}
headersForResume = {'Authorization': 'Bearer SGG2O7HCRGDA4M8NKF3GI8FFL20G6IE2KOOVLCVPIBRCUQQGFO43AVP3R0UHNS86'}

SOFTWARE_NAMES = [SoftwareName.CHROME.value]
OPERATING_SYSTEMS = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
USER_AGENT = UserAgent(software_names=SOFTWARE_NAMES, operating_systems=OPERATING_SYSTEMS, limit=100)
lock = Semaphore(100)

def get_resume_vector(resume):
    filtered_tokens = []
    resume_words_lst = []
    spec_id1 = [role['id'] for role in resume['professional_roles']]
    string = resume['title'].lower() + ' '
    string += ' '.join(resume['skill_set']).lower()

    for dct in resume['experience']:
        string += dct['description'].lower() + ' '
    
    if resume['skills']:
        string += resume['skills'].lower()
        
    token_str = word_tokenize(string, language='russian')
    for token in token_str:
          if token not in stop_words and token not in punct or token == '#':
              stemmed_token = stemmer.stem(token)
              filtered_tokens.append(stemmed_token)
    resume_words = ' '.join(filtered_tokens)
    resume_words_lst.append(resume_words)
    vectorizer = CountVectorizer(vocabulary=dictionary[spec_id1[0]])
    vector_resume = vectorizer.fit_transform(resume_words_lst)
    return vector_resume.toarray()

def get_vacancy_vector(vacancy):
    filtered_tokens = []
    vacancy_words_lst = []
    spec_id1 = [role['id'] for role in vacancy['professional_roles']]
    string = vacancy['name'].lower() + ' '
    
    for word in vacancy['key_skills']:
        string += word['name'].lower() + ' '
    soup = BeautifulSoup(vacancy['description'], 'html.parser')
    string += soup.text.lower()
    token_str = word_tokenize(string, language='russian')
    for token in token_str:
          if token not in stop_words and token not in punct or token == '#':
              stemmed_token = stemmer.stem(token)
              filtered_tokens.append(stemmed_token)
    vacancy_words = ' '.join(filtered_tokens)
    vacancy_words_lst.append(vacancy_words)
    vectorizer = CountVectorizer(vocabulary=dictionary[spec_id1[0]])
    vector_vacancy = vectorizer.fit_transform(vacancy_words_lst)
    return vector_vacancy.toarray()

def get_cosine_similarity(vec1, vec2):
    return 1 - spatial.distance.cosine(vec1, vec2)

def get_key_skills_rate(resumeSkills, vacancySkills):
 
    resumeSkillsList = []
    vacancySkillsList = []
    counter = 0
    
    remove_digit = str.maketrans('', '', digits)
    remove_punct = str.maketrans('', '', punct)

    for skill in resumeSkills:
        resumeSkillsList.append(skill.lower().translate(remove_digit).translate(remove_punct))
    for skill in vacancySkills:
        
        vacancySkillsList.append(skill.lower().translate(remove_digit).translate(remove_punct))
    
    for i in resumeSkillsList:
        if i in vacancySkillsList:
            counter += 1
    if vacancySkillsList:
        rate = (1/len(vacancySkillsList)*counter)/2
    else:
        rate = 0
    if rate > 0.5:
        rate = 0.5
    return rate

def getVacanciesByParams(searchParams, page):
    
    salary = '&salary=' + str(searchParams["salary"]) if searchParams["salary"] else ''
    
    text = '&text=' + searchParams["text"] + '&search_field=' + searchParams["search_field"] if searchParams["toggleTitle"] else ''
    onlyWithSalary = '&only_with_salary=' + searchParams["only_with_salary"] if searchParams["toggleSalary"] else ''
    experience = '&experience=' + searchParams["experience"] if searchParams['toggleExperience'] else ''

    response = requests.get(f'https://api.hh.ru/vacancies/?area={searchParams["area"]}&period={searchParams["period"]}&per_page={searchParams["per_page"]}&responses_count_enabled={searchParams["responses_count_enabled"]}&page={page}{"".join(searchParams["professional_role"])}{onlyWithSalary}{salary}{experience}&premium=true{"".join(searchParams["employment"])}{text}&currency={searchParams["currency"]}', headers=headersForVacancy)
    # print(response)
    # print(response.json())
    return response.json()

def getVacancy(vacancyPreview, items, vacanciesPreview, resumeVector, resumeKeySkills):
    id = vacancyPreview['id']

    try:
        response = requests.get('https://api.hh.ru/vacancies/' + id, headers=headersForVacancy)
    except:
        response = requests.get('https://api.hh.ru/vacancies/' + id, headers=headersForVacancy)
        
    lock.release()
    vacancy = response.json()
    
    
    while 'errors' in vacancy:
        vacancy = requests.get('https://api.hh.ru/vacancies/' + id, headers=headersForVacancy).json()
    vacancy['currentRate'] = 0
    items.append(vacancy)
    vacancyPreview['experience'] = vacancy['experience']
    vacancyPreview['fullDescription'] = vacancy['description']
    vacancyPreview['keySkills'] = vacancy['key_skills']
    vacancyPreview['employment'] = vacancy['employment']

    vacancyKeySkills = [skill['name'] for skill in vacancy['key_skills']]
    keySkillsRate = get_key_skills_rate(resumeKeySkills, vacancyKeySkills)
    vacancyDescriptionRate = get_cosine_similarity(get_vacancy_vector(vacancy), resumeVector)
    if vacancyDescriptionRate > 0.5:
        vacancyDescriptionRate = 0.5
    
    vacancyPreview['rate'] = round(vacancyDescriptionRate + keySkillsRate, 2)
    vacanciesPreview.append(vacancyPreview)

def getVacanciesByPage(searchParams, page, items, vacanciesPreview, resumeVector, resumeKeySkills):
    thread_pool = []
    vacanciesByParams = getVacanciesByParams(searchParams, page)
    if 'errors' not in vacanciesByParams:
        for vacancyPreview in vacanciesByParams['items']:
            thread = Thread(target=getVacancy, args=(vacancyPreview, items, vacanciesPreview, resumeVector,resumeKeySkills ))
            thread_pool.append(thread)
            thread.start()
            lock.acquire()


        for thread in thread_pool:
            thread.join()
        lock.release()
        return items, vacanciesPreview
    else:
        print('errors')
        return []

def getAreaId(resumeArea):
    defaultArea = 4
    try: 
        response = requests.get('https://api.hh.ru/areas/113', headers=headersForVacancy).json()
        for areas in response['areas']:
            if areas['name'] == resumeArea:
                return areas['id']
            else:
                for area in areas['areas']:
                    if area['name'] == resumeArea:
                        return area['id']
    except: 
        return defaultArea

def getExperience(resume):
    if (resume['total_experience'] != None) and ('month' in resume['total_experience']): 
        years = int(resume['total_experience']['months']) / 12 if resume['total_experience']['months'] else 1
    else: 
        years = 0.5
    if years < 1:
        return 'noExperience', 'Нет опыта'
    elif 1 <= years < 3:
        return 'between1And3', 'От 1 года до 3 лет'
    elif 3 <= years < 6:
        return 'between3And6', '0т 3 до 6 лет'
    elif years >= 6:
        return 'moreThan6', 'Более 6 лет'

def getResume(id):
    resumeResponse = requests.get('https://api.hh.ru/resumes/' + id, headers=headersForResume)
    if resumeResponse.status_code == 200:
        return resumeResponse.json()
    else:
        return False

def getVacancies(resume):
    items = []
    vacanciesPreview = []
    thread_pool = []
    resumeKeySkills = resume['skill_set']
    resumeVector = get_resume_vector(resume)
    searchParams = {
            'text': '+'.join(resume['title'].split()), 
            'search_field': 'name',
            'area': getAreaId(resume['area']['name']),
            'no_magic':'true',
            'professional_role': ['&professional_role=' + item['id'] for item in resume['professional_roles']],
            'period': 30,
            'per_page': 50,
            'experience': resume['total_experience'],
            'salary': resume['salary']['amount'],
            'only_with_salary': 'true',
            'employment': ['&employment=' + employment['id'] for employment in resume['employments']],
            'responses_count_enabled': 'true',
            'toggleExperience': resume['toggleExperience'],
            'toggleSalary': resume['toggleSalary'],
            'toggleTitle': resume['toggleTitle'],
            'currency' : resume['salary']['currency']
        }

    for page in range(2):
        thread = Thread(target=getVacanciesByPage, args=(searchParams, page, items, vacanciesPreview, resumeVector, resumeKeySkills))
        thread_pool.append(thread)
        thread.start()
        lock.acquire()
        time.sleep(0.25)

    for thread in thread_pool:
        thread.join()
    
    return (items, vacanciesPreview)


app = Flask(__name__, static_url_path='')  
CORS(app)


@app.route('/items/rolesandareas', methods=['GET'])  
def getAreasAndRoles():

    with open("/Users/hipsta/Desktop/MyDevelop/LaMa-Assistant/server/roles.json", "r",  encoding="utf-8") as f:
        roles = json.load(f)        

    with open("/Users/hipsta/Desktop/MyDevelop/LaMa-Assistant/server/areas.json", "r",  encoding="utf-8") as f:
        areas = json.load(f)      
  
    return jsonify({'categories': roles['categories'] , 'areas': areas['areas']})


@app.route('/items/<string:resumeId>', methods=['GET'])  
def getItems(resumeId):
    t = time.time()
    resume = getResume(resumeId)   
    if resume:
        if not resume['salary']:
            resume['salary'] = {'amount': '', 'currency' : 'RUR'}

        resume['toggleExperience'] = True
        resume['toggleSalary'] = True
        resume['toggleTitle'] = True
        resume['total_experience'] = getExperience(resume)[0]
        (vacancies, vacanciesPreview) = getVacancies(resume)

        r = jsonify({'items': sorted(vacanciesPreview, key=lambda k: k['rate'], reverse=True) , 'resume': resume})
        return jsonify({'items': sorted(vacanciesPreview, key=lambda k: k['rate'], reverse=True) , 'resume': resume})

    else:
        return jsonify({'items': {}, 'resume': {}})

@app.route('/items/edit', methods=['POST'])  
def getItemsAfterEdit():
    t = time.time()
    response = request.get_json(force=True)
    resume = response['resume']
    values= response['values']
    
    if resume:
        if not resume['salary']:
            resume['salary'] = {'amount': '', 'currency' : 'RUR'}
        if values['professionalRole']:
            resume['professional_roles'] = values['professionalRole']
        resume['area']['name'] = values['area']['name']
        resume['salary']['amount'] = values['salary']
        resume['skills'] = values['description']
        resume['total_experience'] = values['resumExperience']
        resume['title'] = values['title']
        resume['total_experience'] = values['resumExperience']
        resume['toggleExperience'] = values['toggleExperience']
        resume['toggleSalary'] = values['toggleSalary']
        resume['toggleTitle'] = values['toggleTitle']
        resume['skill_set'] = values['skillSet']
        resume['salary']['currency'] = values['currency']
        
        
        (vacancies, vacanciesPreview) = getVacancies(resume)

        return jsonify({'items': sorted(vacanciesPreview, key=lambda k: k['rate'], reverse=True), 'resume': resume})
        
    else:
        return jsonify({'items': {}, 'resume': {}})
# export NODE_OPTIONS=--openssl-legacy-provider
# Получение токена вакансий
# import requests
# response = requests.post('https://hh.ru/oauth/token', data={'client_secret':'SEJEQ0GVK6I7PLJCHC7VIFFIMIDLPM1KECK4UP315NU3I7MLKFCVK84SQEDLGEC0', 'client_id': 'RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70', 'grant_type':'client_credentials'})
# print(response.text)
# {"access_token": "T1F9V1I1930VBO5CLT77CVS57SHKKE47J1MVFQ8ATS84DQ16SM9D8SC28CKJFI2U", "token_type": "bearer"}

# Получение токена резюме - перейти по адресу https://hh.ru/oauth/authorize?response_type=code&client_id=RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70
# Получаем в url code=M1BLBHMAVCF1TMNE3V9J2QSUKVU9D3PK9G2NF4V9H57SB3ISODCCL5DL8GN18UV5
# import requests
# response = requests.post('https://hh.ru/oauth/token', data={'client_secret':'SEJEQ0GVK6I7PLJCHC7VIFFIMIDLPM1KECK4UP315NU3I7MLKFCVK84SQEDLGEC0', 'client_id': 'RDT0RFJHJ50AEQQP8MJ49JB8KE0S9S58NVDMB3JHGG1815445RATC9RDL44K2E70', 'grant_type':'authorization_code', 'code': 'M1BLBHMAVCF1TMNE3V9J2QSUKVU9D3PK9G2NF4V9H57SB3ISODCCL5DL8GN18UV5'})
# print(response.text)

# {"access_token": "RLBEKM511TJ60HI9NV7J3JNLPNCA9353T4SBUNIM3QSODOTK8KPUQUFTA404I3TS", "token_type": "bearer", "refresh_token": "N088A5JHPEB1O596RHVBMUIH0GGRTP4B00GGA2LSB7HOLPBR9I35CF3APM0U5Q87", "expires_in": 1209599}

# Проверка токена 
# import requests
# response = requests.get('https://api.hh.ru/me', headers={'content-type': 'application/json', 'Authorization': 'Bearer JBUDRTVE1KO69Q517Q8I3BPBGS5JF1FNNHFJBSRKU75DIRC97GF59QESGNFL4ST2'})
# print(response.text)
# {"auth_type":"applicant","is_applicant":true,"is_employer":false,"is_admin":false,"is_application":false,"id":"96300944","is_anonymous":false,"email":"andrewhipsta@gmail.com","first_name":"Andrey","middle_name":null,"last_name":"Ovechkin","resumes_url":"https://api.hh.ru/resumes/mine","negotiations_url":"https://api.hh.ru/negotiations","is_in_search":true,"mid_name":null,"employer":null,"personal_manager":null,"manager":null,"phone":"79994624536","counters":{"new_resume_views":13,"unread_negotiations":0,"resumes_count":1}}
# headersForVacancy = {'Authorization': 'Bearer JAT2ON2VA8O2CI8R188N9MGLUSUCNACI2C0BISROPHR5O1KCIB4IKAJ5FLBT91UK'}
# headersForResume = {'Authorization': 'Bearer T8ON34F73LE1D7SQN41D0I009LU1TC69MGCKSM305SRPD6ETSVONFN9SAB90JAQM'}
# resumeResponse = requests.get('https://api.hh.ru/resumes/dbbe6550ff09036b230039ed1f6d7954346563', headers=headersForResume)
    
# print(resumeResponse)
if __name__ == '__main__':  
    app.run(port=5001)

# {"access_token": "JAT2ON2VA8O2CI8R188N9MGLUSUCNACI2C0BISROPHR5O1KCIB4IKAJ5FLBT91UK", "token_type": "bearer"}
# 'Руководитель: IT, информационная и общая безопасность
# https://lamaassistant.com/home?code=KCM3OHDSTCP8REU97CEASV333T5UVJG65ANP9F2P6CSMN0SDT4HEL1DK3I43GKR1

# resume {'access_token': 'T8ON34F73LE1D7SQN41D0I009LU1TC69MGCKSM305SRPD6ETSVONFN9SAB90JAQM', 'token_type': 'bearer', 'refresh_token': 'KSNFTLOPLIJNKDLJLD991SUPEDHR23QFH9B4RT859UUUC9EK8B12H06FMOJC22LR', 'expires_in': 1209599}
# dbbe6550ff09036b230039ed1f6d7954346563%7D
# dbbe6550ff09036b230039ed1f6d7954346563%7D

