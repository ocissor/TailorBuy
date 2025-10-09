
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import os
import urllib.parse
load_dotenv()
password = os.getenv("MONGO_DB_PASSWORD")
p1 = os.getenv("MONGO_DB_URI_P1")
p2 = os.getenv("MONGO_DB_URI_P2")
password = urllib.parse.quote(password)

uri = f"{p1}{password}{p2}"

# Create a new client and connect to the server
client = MongoClient(uri, tlsAllowInvalidCertificates=True)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)