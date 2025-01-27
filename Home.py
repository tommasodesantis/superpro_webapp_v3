import streamlit as st
import streamlit_authenticator as stauth

# Get credentials from secrets
username = st.secrets["authentication"]["username"]
password = st.secrets["authentication"]["password"]

# Create an authentication object
authenticator = stauth.Authenticate(
    credentials={"usernames": {username: {"password": password}}},
    cookie_name="streamlit_auth_cookie",
    key="auth_key"
)

# Show login form
name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")
    st.stop()
elif authentication_status == None:
    st.warning("Please enter your username and password")
    st.stop()

# Page config
st.set_page_config(page_title="SuperPro Designer Web App", page_icon="🏭", layout="wide")

# Title and description
st.title("SuperPro Designer Web App")
st.markdown("""
Welcome to the SuperPro Designer Web App! This comprehensive toolkit is designed to enhance your SuperPro Designer experience with three specialized features:

### 🤖 User Manual Chatbot
- AI-powered assistant for instant SuperPro Designer guidance
- Get answers to specific questions about features and functionalities
- Access step-by-step instructions and best practices
- Learn from practical examples and use cases

### 📊 Techno-economic Report Generator
- Generate detailed technical and economic analysis reports
- Transform your SuperPro Designer data into comprehensive documentation
- Analyze capital investments, operating costs, and key performance indicators
- Get actionable insights and recommendations

### 📅 Scheduling Analyzer
- Optimize your process scheduling and resource utilization
- Identify bottlenecks and efficiency improvements
- Analyze equipment usage and maintenance strategies
- Get data-driven recommendations for batch campaign planning

Select a tool from the sidebar to get started with your analysis!
""")

# Add footer
st.markdown("---")
st.markdown("*Developed by Tommaso De Santis*")
