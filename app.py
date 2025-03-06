import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime, timedelta
import os
import re
import random
import smtplib
from email.mime.text import MIMEText

# --- Configuration ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "techsolidershelpdeskcustomer@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "ildy bkzr zukv iqxu")

# Ensure denied_documents folder exists
if not os.path.exists("denied_documents"):
    os.makedirs("denied_documents")

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect("patient_helpdesk.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            dob TEXT NOT NULL,
            age INTEGER NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            mobile_number TEXT NOT NULL,
            dob TEXT NOT NULL,
            place TEXT NOT NULL,
            insurance_policy TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS denied_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            policy_id TEXT NOT NULL,
            policy_name TEXT NOT NULL,
            denial_reason TEXT NOT NULL,
            document_path TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_user(name, email, dob, age, password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("""
            INSERT INTO users (name, email, dob, age, password)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, dob, age, hashed_password))
        conn.commit()
    st.success("Account registered successfully!")

def get_user(email, password=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and password:
            user_dict = dict(user)
            if bcrypt.checkpw(password.encode('utf-8'), user_dict['password'].encode('utf-8')):
                return user_dict
            return None
        return dict(user) if user else None

def update_password(email, new_password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
        conn.commit()

def save_policy_inquiry(name, age, gender, mobile_number, dob, place, insurance_policy):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO policy_inquiries (name, age, gender, mobile_number, dob, place, insurance_policy, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, age, gender, mobile_number, str(dob), place, insurance_policy, str(datetime.now())))
        conn.commit()
    st.success(f"Recommended Policy: {'Basic Health Insurance' if age < 30 else 'Comprehensive Health Insurance'}")

def save_denied_inquiry(patient_name, patient_id, policy_id, policy_name, denial_reason, document_path=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO denied_inquiries (patient_name, patient_id, policy_id, policy_name, denial_reason, document_path, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (patient_name, patient_id, policy_id, policy_name, denial_reason, document_path, str(datetime.now())))
        conn.commit()
    st.warning(f"Denial Reason: {denial_reason}")
    if document_path:
        st.success("Document uploaded successfully.")

# Initialize database
init_db()

# --- Email Functions ---
def generate_reset_code():
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    st.session_state['reset_code_expiry'] = datetime.now() + timedelta(minutes=10)
    return code

def send_reset_code_email(email, reset_code):
    subject = "Password Reset Code - Patient Helpdesk"
    body = f"Your 6-digit reset code is: {reset_code}\n\nValid for 10 minutes."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# --- Chatbot Logic (Simulating Grok) ---
def grok_response(user_input, chat_history):
    system_prompt = """
    You are a Patient Helpdesk Assistant specialized in insurance policies, claims, and denials. Provide helpful, accurate, and concise responses related to health insurance inquiries, policy details, claim processes, and denial reasons (e.g., 'Insufficient documentation', 'Policy expired'). Focus on policies like Basic Health Insurance and Comprehensive Health Insurance, and assist with resolving denied claims. If the user asks about unrelated topics, politely redirect them to insurance-related queries.
    """
    messages = [{"role": "system", "content": system_prompt}] + chat_history + [{"role": "user", "content": user_input}]
    lower_input = user_input.lower()
    if "policy" in lower_input and "basic" in lower_input:
        return "Basic Health Insurance covers essentials like doctor visits and emergencies, ideal for those under 30."
    elif "policy" in lower_input and "comprehensive" in lower_input:
        return "Comprehensive Health Insurance offers broader coverage, including specialist care, suitable for those over 30."
    elif "denied" in lower_input or "denial" in lower_input:
        return "Claims are often denied due to 'Insufficient documentation' or 'Policy expired'. Check your submission details."
    elif "claim" in lower_input:
        return "To file a claim, submit your patient ID, policy number, and documents via the Denied Inquiry section."
    else:
        return "I’m here to help with insurance questions! Ask about policies, claims, or denials."

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'page_state' not in st.session_state:
    st.session_state.page_state = "home"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'reset_code' not in st.session_state:
    st.session_state.reset_code = None
if 'reset_email' not in st.session_state:
    st.session_state.reset_email = None
if 'reset_code_expiry' not in st.session_state:
    st.session_state.reset_code_expiry = None

# --- Professional Styling with 3D Animated Background ---
st.markdown("""
    <style>
        .stApp { 
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96c93d); 
            background-size: 400% 400%; 
            animation: gradientAnimation 15s ease infinite; 
            color: #ffffff; 
            min-height: 100vh; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
        }
        @keyframes gradientAnimation {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.3) 100%);
            z-index: -1;
            animation: pulse 10s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.05); opacity: 0.7; }
            100% { transform: scale(1); opacity: 0.5; }
        }
        .header { font-size: 36px; font-weight: bold; text-align: center; margin-top: 20px; color: #ffffff; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .subheader { font-size: 20px; text-align: center; margin-bottom: 20px; color: #e0e0e0; }
        .form-container { background: rgba(255, 255, 255, 0.95); padding: 20px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); max-width: 500px; margin: 0 auto; color: #333; }
        .sidebar .sidebar-content { background: #1a3c34; padding: 20px; border-radius: 0 10px 10px 0; box-shadow: 2px 0 10px rgba(0,0,0,0.3); }
        .stButton>button { background: #2a5298; color: #ffffff; border: none; border-radius: 8px; padding: 10px 20px; font-weight: bold; }
        .stButton>button:hover { background: #1e3c72; }
        .button-container { display: flex; justify-content: center; gap: 40px; margin: 20px 0; }
        .chat-container { background: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); max-height: 400px; overflow-y: auto; position: fixed; bottom: 20px; right: 20px; width: 320px; }
        .chat-message { background: #e0e0e0; color: #333; padding: 8px; margin: 5px 0; border-radius: 5px; }
        .user-message { background: #2a5298; color: #ffffff; text-align: right; }
        .footer { text-align: center; margin-top: 40px; font-size: 14px; color: #e0e0e0; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
        .signup-link { text-align: center; margin-top: 10px; }
        .signup-link a { color: #2a5298; font-weight: bold; text-decoration: none; cursor: pointer; }
        .signup-link a:hover { color: #1e3c72; text-decoration: underline; }
    </style>
""", unsafe_allow_html=True)

# --- Main App Logic ---
def main():
    if not st.session_state.logged_in:
        if st.session_state.page_state == "home":
            st.markdown('<div class="header">Patient Helpdesk</div>', unsafe_allow_html=True)
            st.markdown('<div class="subheader">Your Professional Healthcare Assistant</div>', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
                if st.button("Login", key="login_home"):
                    st.session_state.page_state = "login"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
                if st.button("Signup", key="signup_home"):
                    st.session_state.page_state = "signup"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "login":
            st.markdown('<div class="subheader">Login</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("login_form"):
                    email = st.text_input("Email", placeholder="Enter your email")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.form_submit_button("Login"):
                            user = get_user(email, password)
                            if user:
                                st.session_state.logged_in = True
                                st.session_state.user_email = email
                                st.session_state.page_state = "dashboard"
                                st.success(f"Welcome, {user['name']}!")
                                st.rerun()
                            else:
                                st.error("Invalid credentials.")
                    with col2:
                        if st.form_submit_button("Forgot Password"):
                            st.session_state.page_state = "forgot_password"
                            st.rerun()
                    with col3:
                        if st.form_submit_button("Back"):
                            st.session_state.page_state = "home"
                            st.rerun()
                if st.button("Not registered? Sign up here", key="signup_link"):
                    st.session_state.page_state = "signup"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "forgot_password":
            st.markdown('<div class="subheader">Reset Password</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("forgot_password_form"):
                    email = st.text_input("Email", placeholder="Enter your registered email")
                    if st.form_submit_button("Send Reset Code"):
                        user = get_user(email)
                        if user:
                            reset_code = generate_reset_code()
                            st.session_state.reset_code = reset_code
                            st.session_state.reset_email = email
                            if send_reset_code_email(email, reset_code):
                                st.success("Reset code sent to your email!")
                                st.session_state.page_state = "reset_password"
                                st.rerun()
                        else:
                            st.error("Email not found.")
                st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "reset_password":
            st.markdown('<div class="subheader">Enter New Password</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("reset_password_form"):
                    code = st.text_input("6-Digit Code", placeholder="Enter the code")
                    new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password")
                    if st.form_submit_button("Reset Password"):
                        if (code == st.session_state.reset_code and st.session_state.reset_email and 
                            datetime.now() < st.session_state.reset_code_expiry):
                            if new_password == confirm_password:
                                update_password(st.session_state.reset_email, new_password)
                                st.success("Password reset successfully!")
                                st.session_state.page_state = "login"
                                st.rerun()
                            else:
                                st.error("Passwords do not match.")
                        else:
                            st.error("Invalid or expired code.")
                st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "signup":
            st.markdown('<div class="subheader">Signup</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("signup_form"):
                    name = st.text_input("Name", placeholder="Enter your name")
                    email = st.text_input("Email", placeholder="Enter your email")
                    dob = st.text_input("Date of Birth (dd.mm.yyyy)", placeholder="e.g., 25.12.1990")
                    age = st.number_input("Age", min_value=0, max_value=150, step=1)
                    password = st.text_input("Password", type="password", placeholder="Create a password")
                    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.form_submit_button("Signup"):
                            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                                st.error("Invalid email format.")
                            elif not re.match(r"^\d{2}\.\d{2}\.\d{4}$", dob):
                                st.error("Date of Birth must be in dd.mm.yyyy format.")
                            elif password != confirm_password:
                                st.error("Passwords do not match.")
                            elif not all([name, email, dob, age, password]):
                                st.error("Please fill all required fields.")
                            else:
                                save_user(name, email, dob, age, password)
                                st.session_state.page_state = "login"
                                st.rerun()
                    with col2:
                        if st.form_submit_button("Back"):
                            st.session_state.page_state = "home"
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    else:
        with st.sidebar:
            st.markdown(f"**Welcome, {st.session_state.user_email.split('@')[0]}**", unsafe_allow_html=True)
            if st.button("Dashboard", key="dash_sidebar"):
                st.session_state.page_state = "dashboard"
                st.rerun()
            if st.button("Policy Inquiry", key="policy_sidebar"):
                st.session_state.page_state = "policy_inquiry"
                st.rerun()
            if st.button("Denied Inquiry", key="denied_sidebar"):
                st.session_state.page_state = "denied_inquiry"
                st.rerun()
            if st.button("Logout", key="logout_sidebar"):
                st.session_state.logged_in = False
                st.session_state.user_email = None
                st.session_state.page_state = "home"
                st.session_state.chat_history = []
                st.rerun()

        if st.session_state.page_state == "dashboard":
            st.markdown('<div class="header">Dashboard</div>', unsafe_allow_html=True)
            st.markdown('<div class="subheader">Explore Your Options</div>', unsafe_allow_html=True)
            st.markdown('<div class="button-container">', unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Policy Inquiry", key="policy_dash"):
                    st.session_state.page_state = "policy_inquiry"
                    st.rerun()
            with col2:
                if st.button("Denied Inquiry", key="denied_dash"):
                    st.session_state.page_state = "denied_inquiry"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "policy_inquiry":
            st.markdown('<div class="subheader">Policy Inquiry</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("policy_form"):
                    name = st.text_input("Name", placeholder="Enter your name")
                    age = st.number_input("Age", min_value=0, max_value=150, step=1)
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                    mobile_number = st.text_input("Mobile Number", placeholder="10-digit number")
                    dob = st.date_input("Date of Birth")
                    place = st.text_input("Place", placeholder="Enter your location")
                    insurance_policy = st.text_area("Insurance Policy Details", placeholder="Describe your policy")
                    if st.form_submit_button("Submit"):
                        if not re.match(r"^\d{10}$", mobile_number):
                            st.error("Mobile number must be 10 digits.")
                        elif all([name, age, gender, mobile_number, dob, place, insurance_policy]):
                            save_policy_inquiry(name, age, gender, mobile_number, dob, place, insurance_policy)
                        else:
                            st.error("All fields are required.")
                st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.page_state == "denied_inquiry":
            st.markdown('<div class="subheader">Denied Inquiry</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("denied_form"):
                    patient_name = st.text_input("Patient Name", placeholder="Enter patient name")
                    patient_id = st.text_input("Patient ID", placeholder="Enter patient ID")
                    policy_id = st.text_input("Policy ID", placeholder="Enter policy ID")
                    policy_name = st.text_input("Policy Name", placeholder="Enter policy name")
                    document = st.file_uploader("Attach Document", type=["pdf", "png", "jpg", "txt"])
                    if st.form_submit_button("Submit"):
                        if all([patient_name, patient_id, policy_id, policy_name]):
                            denial_reason = "Insufficient documentation" if len(patient_id) < 5 else "Policy expired"
                            document_path = None
                            if document:
                                document_path = f"denied_documents/{patient_id}_{policy_id}_{document.name}"
                                with open(document_path, "wb") as f:
                                    f.write(document.getbuffer())
                            save_denied_inquiry(patient_name, patient_id, policy_id, policy_name, denial_reason, document_path)
                        else:
                            st.error("All fields are required.")
                st.markdown('</div>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            st.markdown("**Patient Assistant**", unsafe_allow_html=True)
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f'<div class="chat-message user-message">{message["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message">{message["content"]}</div>', unsafe_allow_html=True)
            with st.form("chat_form", clear_on_submit=True):
                chat_input = st.text_input("Ask me anything...", key="chat_input")
                if st.form_submit_button("Send"):
                    if chat_input:
                        st.session_state.chat_history.append({"role": "user", "content": chat_input})
                        response = grok_response(chat_input, st.session_state.chat_history)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        st.rerun()
                    else:
                        st.warning("Please enter a message.")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer">© 2025 Patient Helpdesk | Powered by xAI</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
