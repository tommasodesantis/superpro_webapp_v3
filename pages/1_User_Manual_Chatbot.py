import streamlit as st
import os
import openai
from typing import List, Dict, Any, Union
from r2r import R2RClient
from utils.check_auth import check_auth

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

def init_requesty():
    """Initialize OpenAI client with Requesty base URL"""
    return openai.OpenAI(
        base_url="https://router.requesty.ai/v1",
        api_key=st.secrets["REQUESTY_API_KEY"],
        default_headers={
            "HTTP-Referer": "http://localhost:8888",
            "X-Title": "SuperPro Manual Assistant"
        }
    )

def process_with_llm(query: str, context: str, requesty_api_key: str):
    client = init_requesty()
    
    messages = [
        {"role": "system", "content": custom_prompt.format(query=query, context=context)},
        {"role": "user", "content": query}
    ]

    try:
        # Create a completion with streaming
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=messages,
            temperature=0.7,
            stream=True
        )
        
        # Process the stream
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"Streaming error: {str(e)}")
        try:
            # Fallback to non-streaming
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=messages,
                temperature=0.7,
                stream=False
            )
            yield response.choices[0].message.content
        except Exception as e:
            print(f"Non-streaming fallback error: {str(e)}")
            yield f"Error: {str(e)}"

def get_superpro_help(query: str, client: R2RClient, requesty_api_key: str):
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
        yield from process_with_llm(query, context, requesty_api_key)
    except Exception as e:
        yield f"Error: {str(e)}"

# Main interface
# Initialize client
client = R2RClient("https://api.cloud.sciphi.ai")
os.environ["R2R_API_KEY"] = st.secrets["R2R_API_KEY"]
requesty_api_key = st.secrets["REQUESTY_API_KEY"]

# Query input
user_query = st.text_input("Enter your SuperPro Designer question:", 
                          placeholder="e.g., How do I set up a batch process simulation?")

if user_query:
    response_container = st.empty()
    
    # Process the response
    accumulated_text = ""
    for chunk in get_superpro_help(user_query, client, requesty_api_key):
        accumulated_text += chunk
        response_container.markdown("### Response\n" + accumulated_text)
    
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
