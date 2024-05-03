from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
import boto3
import logging
import os
from botocore.exceptions import ClientError

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
                    {"AttributeName": "bucket", "KeyType": "RANGE"},  # Sort key
                ],
                AttributeDefinitions=[
                    {"AttributeName": "tournament", "AttributeType": "S"},
                    {"AttributeName": "bucket", "AttributeType": "S"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 50,
                    "WriteCapacityUnits": 50,
                },
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

    def list_tables(self):
        try:
            tables = []
            for table in self.dyn_resource.tables.all():
                tables.append(table)
        except ClientError as err:
            logger.error(
                "Couldn't list tables. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return tables

    def write_batch(self, data):
        try:
            with self.table.batch_writer() as writer:
                for item in data:
                    writer.put_item(Item=item)
        except ClientError as err:
            logger.error(
                "Couldn't load data into table %s. Here's why: %s: %s",
                self.table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise

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

    def get_data(self, key):
        try:
            response = self.table.get_item(Key=key)
        except ClientError as err:
            logger.error(
                "Couldn't get data from table %s. Here's why: %s: %s",
                self.table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response.get('Item', {})

os.environ['AWS_ACCESS_KEY_ID']='AKIA5FTY6XNS5FUPRJMZ'
os.environ['AWS_SECRET_ACCESS_KEY']='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'

app = Flask(__name__)
bootstrap = Bootstrap(app)
logger = logging.getLogger(__name__)


if 'AWS_ACCESS_KEY_ID' not in os.environ or 'AWS_SECRET_ACCESS_KEY' not in os.environ:
    raise EnvironmentError("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")

region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')  # Default to 'us-east-1' if region is not set
dynamodb_resource = boto3.resource('dynamodb', region_name=region)

# Initialize DynamoDBHandler with boto3 DynamoDB resource
dynamodb_handler=DynamoDBHandler(dynamodb_resource)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    tables = dynamodb_handler.list_tables()
    return render_template('search.html', tables=tables)

@app.route('/search-submit', methods=['POST'])
def searchSubmit():
    filters = {}
    for key in request.form:
        if request.form[key]:
            filters[key] = request.form[key]

    data = dynamodb_handler.get_data(filters)
    return render_template('search-submit.html', data=data)

@app.route('/insert')
def insert():
    return render_template('insert.html')

@app.route('/insert-submit', methods=['POST'])
def insertSubmit():
    data = {
        'tournament': request.form['insertTournament'],
        'p1': request.form['insertTeam1'],
        'p2': request.form['insertTeam2'],
        'score': request.form['insertScore'],
        'winner': request.form['insertWinner'],
        'bracket': request.form['insertBracket']
    }

    dynamodb_handler.add_data(data)
    return render_template('insert-submit.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
