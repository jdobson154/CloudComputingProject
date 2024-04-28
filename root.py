from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import mysql.connector

app = Flask(__name__)
bootstrap = Bootstrap(app)

# MySQL database configuration
db_config = {
    'host': 'cloud.czsymkc0w4m0.us-east-1.rds.amazonaws.com',
    'user': 'cloud',
    'password': 'password',
    'database': 'cloud',
    'port': 3306
}

db = mysql.connector.connect(**db_config)

if db.is_connected():
    print('Connected to the MySQL database!')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search')
def search():
    cursor = db.cursor()
    cursor.execute("SHOW TABLES LIKE 'ssbmTable'")
    table_exists = cursor.fetchone()

    if not table_exists:
        cursor.execute("""
            CREATE TABLE ssbmTable (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tournament VARCHAR(255),
                p1 VARCHAR(255),
                p2 VARCHAR(255),
                score VARCHAR(4),
                winner VARCHAR(255),
                bracket VARCHAR(255)
            )
        """)
        db.commit()

    cursor.execute("SELECT * FROM ssbmTable")
    data = cursor.fetchall()
    cursor.close()

    return render_template('search.html', data=data)


@app.route('/search-submit', methods=['POST'])
def searchSubmit():
    if request.method == 'POST':
        ID = request.form['searchID']
        if ID:
            try:
                ID = int(ID)
            except ValueError:
                ID = None
        tournament = request.form['searchTournament']
        p1 = request.form['searchPlayer1']
        p2 = request.form['searchPlayer2']
        score = request.form['searchScore']
        winner = request.form['searchWinner']
        bracket = request.form['searchBracket']

        ID = '*' if not ID else ID
        tournament = '*' if not tournament else tournament
        p1 = '*' if not p1 else p1
        p2 = '*' if not p2 else p2
        score = '*' if score == 'Any' else score
        winner = '*' if not winner else winner
        bracket = '*' if bracket == 'Any' else bracket

        sql_query = "SELECT * FROM ssbmTable WHERE"
        conditions = []
        if ID != '*':
            conditions.append(f" id = '{ID}'")
        if tournament != '*':
            conditions.append(f" tournament = '{tournament}'")
        if p1 != '*' or p2 != '*':
            conditions.append(f" (p1 = '{p1}' OR p2 = '{p1}' OR p1 = '{p2}' OR p2 = '{p2}')")
        if score != '*':
            conditions.append(f" score = '{score}'")
        if winner != '*':
            conditions.append(f" winner = '{winner}'")
        if bracket != '*':
            conditions.append(f" bracket = '{bracket}'")

        sql_query += " AND ".join(conditions)
        cursor = db.cursor()

        if sql_query == 'SELECT * FROM ssbmTable WHERE':
            cursor.execute("SELECT * FROM ssbmTable")
            return render_template('search.html', data=cursor.fetchall())

        cursor.execute(sql_query)
        data = cursor.fetchall()
        cursor.close()

        return render_template('search-submit.html', data=data)


@app.route('/insert')
def insert():
    return render_template('insert.html')


@app.route('/insert-submit', methods=['POST'])
def insertSubmit():
    cursor = db.cursor()
    if request.method == 'POST':
        tournament = request.form['insertTournament']
        p1 = request.form['insertPlayer1']
        p2 = request.form['insertPlayer2']
        score = request.form['insertScore']
        winner = request.form['insertWinner']
        bracket = request.form['insertBracket']

        if winner == p1 or winner == p2:
            cursor.execute("""INSERT INTO ssbmTable (tournament, p1, p2, score, winner, bracket)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """, (tournament, p1, p2, score, winner, bracket))
            db.commit()
            ID = cursor.lastrowid
            cursor.close()

            return render_template('insert-submit.html', data=[ID, tournament, p1, p2, score, winner, bracket])
        return render_template('insert-submit.html', data='error')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3306)