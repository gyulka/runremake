import random
import time
import requests
from flask import Flask, request
from flask_cors import CORS
from config import *
import json
import sqlite3

app = Flask(__name__)
CORS(app)
dollar = 100
inf = 10000
headers = {'accept': 'application/json, text/plain, */*',
           'accept-encoding': 'gzip, deflate, br',
           'accept-language': 'ru,en;q=0.9',
           'authorization': TOKEN,
           'content-length': '22',
           'content-type': 'application/json;charset=UTF-8',
           'origin': 'https://csgorun.gg',
           'referer': 'https://csgorun.gg/',
           'sec-ch-ua': '"Yandex";v="21", " Not;A Brand";v="99", "Chromium";v="93"',
           'sec-ch-ua-mobile': '?0',
           'sec-ch-ua-platform': '"Windows"',
           'sec-fetch-dest': 'empty',
           'sec-fetch-mode': 'cors',
           'sec-fetch-site': 'same-site',
           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 YaBrowser/21.9.0.1044 Yowser/2.5 Safari/537.36'}


# --------------------------------
def tactic1(lis: list):
    return lis[-1] < 1.2 and lis[-2] < 1.2 and lis[-3] < 1.2 and lis[-4] >= 1.2


def tactic2(lis: list):
    return lis[-1] < 1.2 and lis[-2] < 1.2 and lis[-3] >= 1.2 and lis[-4] < 1.2


def tactic4(lis: list):
    return lis[-1] >= 1.2 and lis[-2] < 1.2 and lis[-3] < 1.2 and lis[-4] >= 1.2 and lis[-5] < 1.2


def tactic3(lis: list):
    if lis[-1] < 1.2 and lis[-2] < 1.2:
        return True


def tactic5(lis: list):
    lis = lis[:-1]
    return lis[-1] < 1.2 and lis[-2] < 1.2 and lis[-3] < 1.2 and lis[-4] >= 1.2


def tactic6(lis: list):
    x = 0
    for i in lis[-4:]:
        if i < 1.2:
            x += 1
    return x >= 3


tactic1.bet = 1.2
tactic2.bet = 1.2
tactic3.bet = 1.2
tactic4.bet = 1.2
tactic5.bet = 1.2
tactic6.bet = 1.2

tactic1.count = 1
tactic2.count = 1  # 2
tactic3.count = 1
tactic4.count = 1
tactic5.count = 1  # 2
tactic6.count = 1

tactics = [tactic1, tactic2, tactic3, tactic5, tactic5]
tactics.sort(key=lambda x: -x.count)


# --------------------------------------

def create_db_connect(db='db.db'):
    return sqlite3.connect(db)


def get_bet_weapon(var=0.1):
    con = create_db_connect()
    return con.execute('select id from weapons where cost<? and cost>?',
                       (inv.get_current_bet() * (1 + var), inv.get_current_bet() * (1 - var))).fetchone()[0]


class Weapon():
    def __init__(self, good_id, self_id, cost):
        self.good_id = good_id
        self.self_id = self_id
        self.cost = cost

    def __eq__(self, other):
        return self.self_id == other.self_id


def update_weapons(lis=None):
    if lis is None:
        lis = []
    con = create_db_connect()
    for i in lis:
        try:
            x = con.execute('select cost from weapons where id=?', (i.good_id,)).fetchone()[0]
            con.execute('update weapons set cost=?,last_cost=? where id=?', (i.cost, x, i.good_id))
            con.commit()
        except Exception as error:
            con.execute('insert into weapons(id,cost) values(?,?)', (i.good_id, i.cost))
            con.commit()


class Tg():
    def __init__(self, tg_token, tg_user_id):
        self.user_id = tg_user_id
        self.tg_token = tg_token

    def method(self, method='getMe', json=None):
        if json is None:
            json = {}
        requests.post(f'https://api.telegram.org/bot{self.tg_token}/{method}', json=json)

    def send_messege(self, text):
        self.method('sendMessage', {'chat_id': self.user_id, 'text': text})


class Inventory:
    def __init__(self, weapons=None):
        self.bet = 0.25
        self.balance = 0.0
        if weapons is None:
            weapons = []
        self.weapons = weapons.copy()

    def sum(self):
        return sum(i.cost for i in self.weapons) + self.balance

    def update_inv(self, lis: list, balance=0.0):
        new = [i for i in lis if i not in self.weapons]
        update_weapons(new)
        self.weapons = lis.copy()
        self.balance = balance
        con = create_db_connect()
        if any(tactic([i[0] for i in con.execute('select coef from crash').fetchall()[-10:-4]]) for tactic in tactics):
            self.change_bet()
        self.make_exchange()

    # def find(self):
    #     con = create_db_connect()
    #     to_try = con.execute('select id from weapons where last_cost<? and last_cost>?',
    #                          (self.bet * 1.1, self.bet * 0.9)).fetchall()
    #     pass  #

    def make_exchange(self):
        to_change = [i.self_id for i in self.weapons if abs(i.cost - self.bet) > 0.1]
        try:
            buy = get_bet_weapon()
        except Exception as error:
            tg.send_messege('не найден предмет помоги мне, пока увеличиваю погрешность')
            # self.find() # не удавшаяся задумка, уходить слишком много временина поиск искомого предмета
            buy = get_bet_weapon(var=0.15)
            to_change = [i.self_id for i in self.weapons if abs(i.cost - buy.cost) > 0.1]

        if to_change or 1.1 * self.bet < self.balance:
            res = requests.post(API_URL + 'marketplace/exchange-items', headers=headers, json={
                'userItemIds': to_change,
                'wishItemIds': [buy]
            })
            if res['error'] and res['error'] == 'Insufficient funds':
                update_weapons([Weapon(good_id=buy, cost=inf, self_id=4)])
        tg.send_messege(str(res.json()))

    def make_bet(self, k=1.2, count=1):
        x = 1
        response = requests.post(API_URL + 'make-bet', headers=headers, json={
            'userItemIds': [i.self_id for i in self.weapons if abs(i.cost - self.bet) < self.bet * 0.1][:count],
            'auto': f'1.{random.randint(18, 22)}'
        })
        while (not response) and x < 7:
            response = requests.post(API_URL + 'make-bet', headers=headers, json={
                'userItemIds': [i.self_id for i in self.weapons if abs(i.cost - self.bet) < self.bet * 0.1][:count],
                'auto': f'1.{random.randint(18, 22)}'
            })
            time.sleep(1)
            x += 1
            print(response.text)

    def to_withdraw(self):
        return random.choice(self.weapons)

    def withdraw(self):
        res = requests.post(API_URL + 'withdraw', headers=headers,
                            json={'email': EMAIL, 'isGoodasly': True, 'userItemId': inv.to_withdraw().self_id})

        tg.send_messege(f'заказан вывод средсв,{inv.to_withdraw().cost}$={inv.to_withdraw().cost * dollar}')

    def change_bet(self):
        # https://en.wikipedia.org/wiki/Kelly_criterion
        # сумма ставки будет зависеть от текущего баланса
        # все стретегии расчитаны под коэф. 1.2, шанс 88%
        # шанс не постоянный, и из-за рандома варьируется в пределах одного процента
        # конкретно нам нужна gambling formula
        # f=p-q/b где
        # p вероятность выигрыша
        # q вероятность проигрыша (1-p)
        # b - относительный выигрыш (коэф.-1)
        p = 0.88
        q = 1 - p
        b = 1.2 - 1.0
        f = p - q / b
        self.bet = f * self.sum()
        self.bet = round(self.bet, 2)
        tg.send_messege(f'ставка изменена {self.bet}')

    def get_current_bet(self):
        return self.bet


@app.route('/')
def func():
    return 'Hell'


@app.route('/get_token', methods=['GET'])
def get_token():
    return TOKEN


@app.route('/append', methods=['POST'])
def append():
    dict1 = json.loads(request.data.decode('utf-8'))
    con = create_db_connect()
    try:
        time.sleep(1)
        con.execute('insert into crash(id,coef) values(?,?)', (dict1['id'], dict1['crash']))
        con.commit()
        if dict1['id'] % 200 == 0:
            tg.send_messege(f'баланс: {inv.sum()}')
        x = con.execute('select coef from crash').fetchall()[-7:]
        x = [i[0] for i in x]
        for i in tactics:
            if i(x):
                inv.make_bet(i.bet, i.count)
                break

    except sqlite3.IntegrityError as error:
        pass
    return 'ok'


@app.route('/update_inv', methods=['POST'])
def update_inv():
    try:
        dict2 = json.loads(request.data.decode('utf-8'))
        inv.update_inv(
            list(map(lambda x: Weapon(self_id=x['id'], good_id=x['itemId'], cost=x['price']), dict2['userItemIds'])),
            dict2['balance'])
        return {'success': True}
    except Exception:
        return {'success': False}


@app.route('/update_bet')
def update_bet():
    inv.change_bet()
    return 'ok'


if __name__ == '__main__':
    inv = Inventory()
    tg = Tg(TG_TOKEN, TG_USER_ID)
    tg.send_messege('я включился')
    app.run()
