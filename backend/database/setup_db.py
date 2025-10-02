from pinecone import Pinecone, ServerlessSpec
import os
from Config.config import Config
pc = Pinecone(api_key=Config.PINECONE_API_KEY)

index_name = "flipkart-product-recommender"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=768,
        spec = ServerlessSpec(cloud = "aws", region = "us-east-1")
    )