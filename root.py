from flask import Flask, render_template, request, redirect, url_for
from flask_bootstrap import Bootstrap
import boto3
import logging
import os
import botocore
from botocore.exceptions import ClientError

os.environ['AWS_ACCESS_KEY_ID'] = ''  # !!!!!
os.environ['AWS_SECRET_ACCESS_KEY'] = ''  # !!!!!

app = Flask(__name__)
bootstrap = Bootstrap(app)
logger = logging.getLogger(__name__)

if 'AWS_ACCESS_KEY_ID' not in os.environ or 'AWS_SECRET_ACCESS_KEY' not in os.environ:
    raise EnvironmentError(
        "AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")

region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')  # Default to 'us-east-1' if region is not set
dynamodb_resource = boto3.resource('dynamodb', region_name=region)


class DynamoDBHandler:
    def __init__(self, dyn_resource):
        self.dyn_resource = dyn_resource
        self.table = None

    def exists(self, table_name):
        try:
            table = self.dyn_resource.Table(table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                logger.error(
                    "Couldn't check for existence of %s. Here's why: %s: %s",
                    table_name,
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise
        else:
            self.table = table
        return exists

    def create_table(self, table_name):
        try:
            self.table = self.dyn_resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "tournament", "KeyType": "HASH"},  # Partition key
                    {"AttributeName": "id", "KeyType": "RANGE"},  # Sort key
                ],
                AttributeDefinitions=[
                    {"AttributeName": "tournament", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "N"}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            self.table.wait_until_exists()
        except ClientError as err:
            logger.error(
                "Couldn't create table %s. Here's why: %s: %s",
                table_name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return self.table

    def add_data(self, data):

        try:
            self.table.put_item(Item=data)
        except ClientError as err:
            logger.error(
                "Couldn't add data to table %s. Here's why: %s: %s",
                self.table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise


def generateID():
    table = dynamodb_resource.Table('lolTable')
    response = table.scan()
    tableEntries = response['Items']

    if len(tableEntries) == 0:
        return 1

    idList = []
    for entry in tableEntries:
        idList.append(entry['id'])

    nextID = max(idList) + 1
    return nextID


def generateQuery(keys):
    table = dynamodb_resource.Table('lolTable')
    filters = {}
    filterExp = ''
    expAttrVals = {}
    expAttrNames = {}

    for key in keys:
        if request.form[key]:
            filters[key] = request.form[key]

    for i, (key, value) in enumerate(filters.items(), start=1):
        expAttrNameKey = f'#attr{i}'
        expAttrValKey = f':val{i}'
        expAttrNames[expAttrNameKey] = key
        expAttrVals[expAttrValKey] = int(value) if key == 'id' else value
        filterExp += f'{expAttrNameKey} = {expAttrValKey} AND '

    if filterExp:
        filterExp = filterExp[:-5]

    response = table.scan(
        FilterExpression=filterExp,
        ExpressionAttributeNames=expAttrNames,
        ExpressionAttributeValues=expAttrVals
    )

    return response


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search')
def search():
    data = []
    table = dynamodb_resource.Table('lolTable')
    response = table.scan()
    tableEntries = response['Items']

    for entry in tableEntries:
        newEntry = []

        for i in range(len(entry)):
            newEntry.append(entry['id'])
            newEntry.append(entry['tournament'])
            newEntry.append(entry['t1'])
            newEntry.append(entry['t2'])
            newEntry.append(entry['score'])
            newEntry.append(entry['winner'])
            newEntry.append(entry['bracket'])

        data.append(newEntry)

    return render_template('search.html', data=data)


@app.route('/search-submit', methods=['POST'])
def searchSubmit():
    data = []
    keys = request.form.keys()

    try:
        response = generateQuery(keys)
        tableEntries = response['Items']

        for entry in tableEntries:
            newEntry = [entry.get(key, '') for key in keys]
            data.append(newEntry)

        return render_template('search-submit.html', data=data)

    except botocore.exceptions.ClientError:
        return redirect(url_for('search'))


@app.route('/insert')
def insert():
    return render_template('insert.html')


@app.route('/insert-submit', methods=['POST'])
def insertSubmit():
    data = {
        'id': generateID(),
        'tournament': request.form['insertTournament'],
        't1': request.form['insertTeam1'],
        't2': request.form['insertTeam2'],
        'score': request.form['insertScore'],
        'winner': request.form['insertWinner'],
        'bracket': request.form['insertBracket']
    }

    # Check if the winner is either t1 or t2
    if data['winner'] != data['t1'] and data['winner'] != data['t2']:
        message = "Invalid winner entered. Winner must be either Team 1 or Team 2."
        logger.error(message)
        return render_template('insert-submit.html', data='error', message=message)

    handler.add_data(data)
    return render_template('insert-submit.html', data=data)


if __name__ == '__main__':

    tableName = "lolTable"
    handler = DynamoDBHandler(dynamodb_resource)

    if not handler.exists(table_name=tableName):
        handler.create_table(tableName)

    app.run(host='0.0.0.0', port=11278)