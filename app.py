from random import *
from flask import Flask, render_template, jsonify, request, redirect, url_for
import jwt
from pymongo import MongoClient
import hashlib
import datetime

app = Flask(__name__)
app.config.from_object('satcounter_config')

client = MongoClient('localhost', 27017)
db = client.JungleGYM

SECRET_KEY = 'jungle'

nextId = -1 
id_list = []

# 맨 처음 로그인 화면
@app.route('/')
def home():
    return render_template('login.html')
    
@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/auth', methods=['POST'])
def api_auth():
    token_receive = request.form['token']
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']}, {"_id": 0})
        return render_template('main.html', username=user_info['name'])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/sign_up')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def api_register():
    name_receive = request.form['name_give']
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    pw2_receive = request.form['pw2_give']

    aa = db.user.find_one({'id': id_receive})
    if (id_receive == '') or (pw_receive == ''):
        return jsonify({'result': 'fail', 'msg': 'ID/PW를 입력해주세요.'})
    elif aa is not None:
        print(aa)
        print('동일한 ID가 존재합니다. 다른 ID를 입력해주세요.')
        return jsonify({'result': 'fail', 'msg': '동일한 ID가 존재합니다. 다른 ID를 입력해주세요.'})

    elif pw_receive != pw2_receive:
        print('비밀번호가 일치하지 않습니다. 다시 확인해주세요.')
        return jsonify({'result': 'fail', 'msg': '비밀번호가 일치하지 않습니다. 다시 확인해주세요.'})

    else:
        print(id_receive)
        pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
        doc = {
            'name' : name_receive,
            'id' : id_receive,
            'pw' : pw_hash,
        }
        db.user.insert_one(doc)

        return jsonify({'result': 'success', 'msg': '회원가입이 완료 되었습니다! 로그인 페이지로 이동합니다.'})

@app.route('/idcheck', methods=['POST'])
def idcheck():
    id_receive = request.form['id_give']
    print(id_receive)

    aa = db.user.find_one({'id': id_receive}, {'_id': False})
    print(aa)
    if id_receive == '':
        return jsonify({'msg': 'ID를 입력해주세요.'})
    elif aa is not None:
        print('동일한 ID가 존재합니다. 다른 ID를 입력해주세요.')
        return jsonify({'msg': '동일한 ID가 존재합니다. 다른 ID를 입력해주세요.'})
    else:
        print('사용 가능한 ID입니다.')
        return jsonify({'msg': '사용 가능한 ID입니다.'})
    
@app.route('/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    if (id_receive=='') or (pw_receive==''):
        return jsonify({'result': 'fail', 'msg': '아이디,패스워드를 입력하세요.'})
    
    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})
   

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)    #언제까지 유효한지
        }
        #jwt를 암호화
        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        

        # 모든 문서를 불러오는 고유 Primary key는 id로 설정
        global unique
        unique = id_receive

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})    


## 4-) 로그인 되었을 때, main.html로 이동 
@app.route('/main', methods=['GET'])
def main(): 

    # DB에 있는 정보들 다 불러오기
    memos = list(db.memos.find({}, {'_id' : False}).sort('cnt'))

    # 화면을 띄울 때, 메모 카드들을 불러옴과 동시에 id_list를 셋팅한다.
    # 새로고침 하더라도 id_list에 card_id들이 중복되어 들어가지 않도록 한다.
    global id_list
    temp = list(db.memos.find({}, {'_id': False, 'level': False, 'sport': False, 'time': False, 'spot': False, 'gender': False, 'text': False, 'cnt': False}))
    for one in temp:
        card_id = one['card_id']
        if card_id not in id_list:
            id_list.append(card_id)

    return render_template('listing.html', memos=memos)

## 6-) 
@app.route('/main/posting', methods=['POST'])
def posting():
    # 1) 클라이언트로부터 데이터를 받는다.
    level = request.form['level']
    sport = request.form['sport']
    time = request.form['time']
    spot = request.form['spot']
    gender = request.form['gender']
    text = request.form['text']

    token_receive = request.form['token']
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    userinfo = db.user.find_one({"id": payload['id']}, {"_id": 0})
    username = userinfo['name']
    
    # 2) mongoDB에 데이터를 넣는다. (도큐먼트를 생성할 때마다, 고유의 id 값을 부여한다.)
    global nextId
    global id_list
    while True:
        nextId = randint(1, 1024)
        if nextId in id_list:
            continue
        else :
            id_list.append(nextId)
            break

    memo = {'card_id': nextId, 'level': level, 'sport': sport, 'time': time, 'spot': spot, 'gender': gender, 'creator': username, 'text': text, 'cnt': 0, 'm1': '', 'm2': '','m3': ''}
    db.memos.insert_one(memo)


    # 4) 성공하면, success 메시지를 보낸다.
    return jsonify({'result': 'success'})

@app.route('/main/finding', methods=['POST'])
def finding(): 
    # 1) 클라이언트로부터 데이터를 받는다.
    level_find = request.form['level']
    sport_find = request.form['sport']
    time_find = request.form['time']
    spot_find = request.form['spot']
    gender_find = request.form['gender']
    # DB에 있는 정보들 다 불러오기

    memos = list(db.memos.find({'level': level_find, 'sport': sport_find, 'time': time_find, 'spot': spot_find, 'gender': gender_find}, {'_id' : False}).sort('cnt'))
    
    print(memos)
    # 화면을 띄울 때, 메모 카드들을 불러옴과 동시에 id_list를 셋팅한다.
    # 새로고침 하더라도 id_list에 card_id들이 중복되어 들어가지 않도록 한다.
    
    return jsonify({"result":"success", "memos" : memos})


@app.route('/main/join', methods=['POST'])
def join():
    card_id_receive = request.form['card_id']
    token_receive = request.form['token']
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    userinfo = db.user.find_one({"id": payload['id']}, {"_id": 0})
    member = userinfo['name']
    int_id = int(card_id_receive)
    memo = db.memos.find_one({'card_id': int_id})
    member_cnt = memo['cnt'] + 1
    
    m1 = memo['m1']
    m2 = memo['m2']
    m3 = memo['m3']
    if m1 == "":
        db.memos.update_one({'card_id' : int_id}, {'$set': {'cnt': member_cnt, 'm1': member}})
    elif m2 == "":
        db.memos.update_one({'card_id' : int_id}, {'$set': {'cnt': member_cnt, 'm2': member}})
    elif m3 == "":
        db.memos.update_one({'card_id' : int_id}, {'$set': {'cnt': member_cnt, 'm3': member}})
    else:
        return jsonify({'result' : 'fail'})
    return jsonify({'result': 'success'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)