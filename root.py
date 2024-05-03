from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import boto3
import os

app = Flask(__name__)
bootstrap = Bootstrap(app)

if 'AKIA5FTY6XNS5FUPRJMZ' in os.environ and 'LiKUUEGf5Pn1DNQjl/EtA0deFGMBT4tADkiO+iaE' in os.environ:
    aws_access_key_id = os.environ['AKIA5FTY6XNS5FUPRJMZ']
    aws_secret_access_key = os.environ['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']
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1', aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
else:
    dynamodb=boto3.resource('dynamodb',region_name='us-east-1')

table_name='ssbmTable'
table=dynamodb.Table(table_name)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search')
def search():
    response = table.scan()
    data=response.get('Items',[])
    return render_template('search.html',data=data)


@app.route('/search-submit', methods=['POST'])
def searchSubmit():
    if request.method == 'POST':
        ID = request.form['searchID']
        tournament = request.form['searchTournament']
        p1 = request.form['searchPlayer1']
        p2 = request.form['searchPlayer2']
        score = request.form['searchScore']
        winner = request.form['searchWinner']
        bracket = request.form['searchBracket']

        filters={}
        if ID:
            filters['id'] = ID
        if tournament:
            filters['tournament'] = tournament
        if p1 or p2:
            filters['p1'] = p1
            filters['p2'] = p2
        if score != 'Any':
            filters['score'] = score
        if winner:
            filters['winner'] = winner
        if bracket != 'Any':
            filters['bracket'] = bracket

        response = table.scan(FilterExpression=' and '.join([f'#{key} = :{key}' for key in filters.keys()]),
                              ExpressionAttributeNames={f'#{key}': key for key in filters.keys()},
                              ExpressionAttributeValues={f':{key}': value for key, value in filters.items()})
        data = response.get('Items', [])
        return render_template('search-submit.html', data=data)


@app.route('/insert')
def insert():
    return render_template('insert.html')


@app.route('/insert-submit', methods=['POST'])
def insertSubmit():
    if request.method == 'POST':
        tournament = request.form['insertTournament']
        p1 = request.form['insertPlayer1']
        p2 = request.form['insertPlayer2']
        score = request.form['insertScore']
        winner = request.form['insertWinner']
        bracket = request.form['insertBracket']

        response = table.put_item(
            Item={
                'tournament': tournament,
                'p1': p1,
                'p2': p2,
                'score': score,
                'winner': winner,
                'bracket': bracket
            }
        )


        ID = response['Attributes']['id']

        return render_template('insert-submit.html', data=[ID, tournament, p1, p2, score, winner, bracket])

    return render_template('insert-submit.html', data='error')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
