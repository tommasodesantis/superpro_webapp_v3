import streamlit as st
import os
import json
import requests
import aiohttp
import nest_asyncio
from typing import List, Dict, Any, Union, AsyncGenerator
from r2r import R2RClient
from utils.check_auth import check_auth

# Enable nested asyncio
nest_asyncio.apply()

# Page config
st.set_page_config(page_title="User Manual Chatbot", page_icon="📚")

# Check authentication
check_auth()

# Title and description
st.title("SuperPro User Manual Chatbot (multilingual)")
with st.expander("Instructions", expanded=False):
    st.markdown("""
    Your intelligent and multilingual assistant for SuperPro Designer guidance! This AI-powered chatbot helps you:

    - Find specific information from the SuperPro Designer manual instantly
    - Get step-by-step instructions for complex operations
    - Understand best practices and recommended workflows
    - Troubleshoot common issues and challenges

    Simply type your question below - for example:
    - "How do I set up a batch process simulation?"
    - "What's the difference between procedure and operation modes?"
    - "How can I optimize my equipment sizing?"
    - "What factors affect scheduling calculations?"

    The chatbot will provide clear, accurate answers with references to the official manual.
    """)

# Custom system prompt
custom_prompt = """You are a SuperPro Designer expert focused on helping users understand and utilize the software effectively. Your purpose is to:

1. Quickly retrieve and explain SuperPro Designer features and functionalities
2. Help users understand process modeling and simulation capabilities
3. Provide clear, practical guidance with proper references to the user manual

When responding:
- Always cite specific sections from the SuperPro Designer user manual
- Provide step-by-step instructions when applicable
- Highlight any limitations or specific requirements
- Include relevant examples or use cases when possible

Query: {query}

Context: {context}

Response:"""

def parse_sse_chunk(chunk: bytes) -> str:
    """Parse a chunk of SSE data and extract the content."""
    if not chunk:
        return ""
    
    try:
        data = json.loads(chunk.decode('utf-8').split('data: ')[1])
        if data.get('choices') and len(data['choices']) > 0:
            delta = data['choices'][0].get('delta', {})
            return delta.get('content', '')
    except (json.JSONDecodeError, IndexError, KeyError):
        pass
    return ""

async def process_with_llm(query: str, context: str, openrouter_api_key: str) -> AsyncGenerator[str, None]:
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8888",
        "X-Title": "SuperPro Manual Assistant"
    }
    
    messages = [
        {"role": "system", "content": custom_prompt.format(query=query, context=context)},
        {"role": "user", "content": query}
    ]
    
    provider_config = {
        "order": ["Lepton", "Together", "Avian"],
        "allow_fallbacks": True
    }

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
        "provider": provider_config
    }

    async def stream_response():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    async for line in response.content:
                        if line:
                            content = parse_sse_chunk(line)
                            if content:
                                yield content
        except Exception as e:
            print(f"Streaming error: {str(e)}")
            # Fallback to non-streaming
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={**payload, "stream": False}
            )
            result = response.json()
            yield result["choices"][0]["message"]["content"]

    async for chunk in stream_response():
        yield chunk

async def get_superpro_help(query: str, client: R2RClient, openrouter_api_key: str) -> AsyncGenerator[str, None]:
    """Function to query the SuperPro Designer knowledge base"""
    try:
        # Get top 30 chunks
        chunks = client.retrieval.search(
            query=query,
            search_settings={
                "limit": 30
            }
        )
        
        # Join chunks into context
        context = "\n\n".join([chunk["text"] for chunk in chunks["results"]["chunk_search_results"]])
        
        # Process with LLM
        async for chunk in process_with_llm(query, context, openrouter_api_key):
            yield chunk
    except Exception as e:
        yield f"Error: {str(e)}"

# Main interface
# Initialize client
client = R2RClient("https://api.cloud.sciphi.ai")
os.environ["R2R_API_KEY"] = st.secrets["R2R_API_KEY"]
openrouter_api_key = st.secrets["OPENROUTER_API_KEY"]

# Query input
user_query = st.text_input("Enter your SuperPro Designer question:", 
                          placeholder="e.g., How do I set up a batch process simulation?")

if user_query:
    response_container = st.empty()
    import asyncio
    
    async def process_stream():
        accumulated_text = ""
        async for chunk in get_superpro_help(user_query, client, openrouter_api_key):
            accumulated_text += chunk
            response_container.markdown("### Response\n" + accumulated_text)
    
    with st.spinner("Generating response..."):
        asyncio.run(process_stream())
    
    # Add a divider
    st.markdown("---")
    
    # Show previous questions (if any)
    if 'previous_queries' not in st.session_state:
        st.session_state.previous_queries = []
    
    if user_query not in st.session_state.previous_queries:
        st.session_state.previous_queries.append(user_query)
    
    if st.session_state.previous_queries:
        st.markdown("### Previous Questions")
        for q in reversed(st.session_state.previous_queries[-5:]):  # Show last 5 questions
            st.text(f"• {q}")
