import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

class Database:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client['discord_bot_db']
        
    def get_collection(self, collection_name):
        return self.db[collection_name]

db = Database()