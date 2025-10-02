from langchain_core.prompts import PromptTemplate 

template_str = """You are a helpful product recommendation assistant for an e-commerce website.

User query:
{user_query}

Previous conversation history:
{chat_history}

Relevant product information and context:
{context}

Based on the above, provide a concise and relevant list of product recommendations tailored to the user's needs. 
Focus on accuracy and helpfulness."""


    # Create a PromptTemplate with one input variable
rag_prompt = PromptTemplate.from_template(template_str)
