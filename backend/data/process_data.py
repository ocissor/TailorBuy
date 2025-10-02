import os
import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
import uuid
from pathlib import Path
import os
import json
from backend.database.setup_db import pc, index_name
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import requests
from io import BytesIO
import base64
from Config.config import Config
import time
import warnings
warnings.filterwarnings("ignore")
from tqdm import tqdm

os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY

index = pc.Index(index_name)
index.delete(delete_all = True)
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")  
checkpoint = None
def generate_image_description(image_url:str):
    # Initialize model
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")
    instruction = '''    Generate a detailed description of a clothing item in an image.

                        The LLM should:
                        - Focus **only** on the clothing item(s) present in the image.
                        - Ignore the person wearing it, the background, accessories, or any other objects.
                        - Describe the clothing item in as much detail as possible, including:
                            - Type of clothing (shirt, dress, jacket, pants, etc.)
                            - Color(s) and patterns
                            - Fabric or material (if discernible)
                            - Fit, style, or cut (e.g., slim-fit, oversized, A-line)
                            - Distinctive features (buttons, collars, cuffs, prints, logos, embroidery)
                        - Provide a concise, informative, and visually grounded description.
                    '''
    # Read and encode image
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            image_data = base64.b64encode(BytesIO(response.content).read()).decode()

            # Prepare message with text and image
            message = HumanMessage(
                content=[
                    {"type": "text", "text": instruction},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_data}"},
                ]
            )

            # Invoke model
            response = llm.invoke([message])
            return response.content

        else:
            return None
        
    except Exception as e:
        print(f"Request failed: {e}")
        return None
        

def data_ingestion(data_dir:str, file:str, idx:int = None):

    vectors = []
    file_path = data_dir/file
    with open(file_path, "r", encoding="utf-8") as f:
        scrapped_data = json.load(f)
    
    for i, data in enumerate(tqdm(scrapped_data)):
        desc = generate_image_description(data['thumbnailImage'])
        if desc:
            vectors.append({"id":str(uuid.uuid4()), "values":embeddings.embed_query(str(desc)), 
                            "metadata":{"brand":data['brand'], 
                                        "title":data['title'],
                                        "url":data['url'],
                                        "description":desc,
                                        "thumbnailImage": data["thumbnailImage"],
                                        'stars':data['stars']
                                        }})
            with open(data_dir/"checkpoint.txt", "w") as f:
                f.write(f"file path is {file_path} and data idx is {i}")


        time.sleep(4)
    index.upsert(vectors = vectors)

if __name__ == "__main__":
    data_dir = Path(__file__).parent
    checkpoint_file = data_dir/"checkpoint.txt"
    
    for file in os.listdir(data_dir):
        if file.endswith(".json"):
            data_ingestion(data_dir,file)

