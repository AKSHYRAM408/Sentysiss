import time
import re
import os
import requests
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables for local developmen
GROK_API_KEY = st.secrets["GROQ_API_KEY"]
if not GROK_API_KEY:
    st.error("Error: GROK_API_KEY is not set. Check your .env file or Streamlit secrets.")
    st.stop()

GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Function to scrape Instagram comments
def scrape_instagram_comments(reel_url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(reel_url)
    time.sleep(5)

    comments_elements = driver.find_elements(By.CSS_SELECTOR, "ul li span")
    comments = [comment.text for comment in comments_elements]

    driver.quit()
    return comments

# Function to scrape YouTube comments
def scrape_youtube_comments(video_url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(video_url)
    time.sleep(10)

    # Scroll multiple times to load more comments
    body = driver.find_element(By.TAG_NAME, "body")
    for _ in range(5):
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(2)

    comments_elements = driver.find_elements(By.CSS_SELECTOR, "#content-text")
    comments = [comment.text for comment in comments_elements]

    driver.quit()
    return comments

# Function to clean comments
def clean_comment(comment):
    return re.sub(r'[^\w\s.,!?\'"-]', '', comment)

spam_keywords = ["follow me", "free money", "click this link", "DM us", "buy followers", "promotion", "promo code", "earn cash", "instant profit"]

# Function to detect spam percentage
def detect_spam(comments):
    spam_keywords = ["follow me", "free money", "click this link", "DM us", "buy followers", "promotion", "promo code", "earn cash", "instant profit"]
    total_comments = len(comments)
    spam_count = sum(1 for comment in comments if any(keyword in comment.lower() for keyword in spam_keywords))

    if total_comments > 0:
        spam_percentage = (spam_count / total_comments) * 100
    else:
        spam_percentage = 0

    return round(spam_percentage, 2)

# Function to analyze comments with Grok AI
def analyze_comments_with_grok(comments, spam_keywords):
    messages = [
        {"role": "system", "content": "You are an expert social media analyst."},
        {"role": "user", "content": f"Analyze these comments:\n\n{comments}\n\n"
                                     "Tasks:\n"
                                     "1. Determine the positive reach (engagement sentiment).\n"
                                     "2. Identify negative reach (if any).\n"
                                     "3. Detect spam based on patterns such as repetitive messages, excessive promotions, unnatural text, bot-like behavior, or links.\n"
                                     "4. Suggest improvements for better audience interaction.\n"
                                     "5. Provide two actionable recommendations to boost engagement.\n"
                                     "6. Report the spam detected and explain why those messages were classified as spam.\n\n"
                                     "Format your response as:\n"
                                     "All responses should not exceed 100 words\n"
                                     "- Positive Reach: (percentage or description)\n"
                                     "- Negative Reach: (percentage or description)\n"
                                     "- Suggested Improvements: (list)\n"
                                     "- Recommendations (two points): (list)\n"}
    ]

    payload = {
        "model": "llama3-8b-8192",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 350
    }

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROK_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response from AI.")
    else:
        return f"Error: {response.status_code} - {response.text}"

# Streamlit UI Setup
st.set_page_config(page_title="Social Media Comment Analyzer", page_icon="📲", layout="wide")

st.markdown("""
    <style>
    body {
        background-color: #121212;
        color: #ffffff;
    }
    .stApp {
        background-color: #121212;
    }
    .stTextInput, .stTextArea {
        background-color: #1E1E1E;
        color: #ffffff;
        border-radius: 10px;
        text-align: center;
    }
    .stButton > button {
        background-color: #E1306C;
        color: white;
        border-radius: 10px;
        font-size: 16px;
        width: 250px;
        display: block;
        margin: auto;
    }
    .stButton > button:hover {
        background-color: #C13584;
    }
    .stContainer {
        padding: 20px;
        border-radius: 10px;
        background-color: #1E1E1E;
        box-shadow: 0px 0px 15px rgba(255, 255, 255, 0.1);
        margin: auto;
        width: 80%;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #E1306C;'>📲 Social Media Comment Analyzer</h1>", unsafe_allow_html=True)

# Input for URL
st.markdown("<div class='stContainer'>", unsafe_allow_html=True)
url = st.text_input("Enter Instagram or YouTube URL:", help="Paste the link of the post/video you want to analyze.")
st.markdown("</div>", unsafe_allow_html=True)

# Centering the Button
st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
analyze_button = st.button("Analyze Comments")
st.markdown("</div>", unsafe_allow_html=True)

if analyze_button:
    if url:
        with st.spinner("Detecting platform and scraping comments..."):
            if "instagram.com" in url:
                platform = "Instagram"
                comments = scrape_instagram_comments(url)
            elif "youtube.com" in url or "youtu.be" in url:
                platform = "YouTube"
                comments = scrape_youtube_comments(url)
            else:
                st.error("Invalid URL. Please enter a valid Instagram or YouTube link.")
                st.stop()

            cleaned_comments = [clean_comment(comment) for comment in comments]
            comments_text = "\n".join(cleaned_comments)

        st.success(f"Comments scraped successfully from {platform}!")

        with st.spinner("Analyzing comments with AI..."):
            ai_response = analyze_comments_with_grok(comments_text, spam_keywords)

        spam_percentage = detect_spam(cleaned_comments)

        st.subheader(f"💡 AI Insights on {platform}:")
        st.write(ai_response)
    else:
        st.error("Please enter a valid URL.")
