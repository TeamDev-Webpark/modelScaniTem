"""
Authentication and user management for the Admin backend.
Uses bcrypt for secure password hashing with fallback to hashlib.
"""
from datetime import datetime
import streamlit as st
from core.config import ADMIN_DEFAULT_USER, ADMIN_DEFAULT_PASS
from core.db import get_db, check_connection
from core.models_db import User

# Safe password hashing with bcrypt or hashlib fallback
try:
    import bcrypt
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False
except ImportError:
    import hashlib
    def hash_password(password: str) -> str:
        return "sha256$" + hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if hashed_password.startswith("sha256$"):
            return hashed_password == "sha256$" + hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return False


def ensure_default_admin():
    """
    Ensures that at least one admin user exists in the database.
    If no admin exists, creates one with credentials from config.
    """
    is_ok, _ = check_connection()
    if not is_ok:
        return
    
    try:
        with get_db() as db:
            existing = db.query(User).filter(User.username == ADMIN_DEFAULT_USER).first()
            if not existing:
                admin_user = User(
                    username=ADMIN_DEFAULT_USER,
                    password_hash=hash_password(ADMIN_DEFAULT_PASS),
                    role="admin"
                )
                db.add(admin_user)
                # Commit handled by context manager
    except Exception as e:
        st.warning(f"Note: Could not verify/create default admin: {e}")


def authenticate(username: str, password: str) -> User | None:
    """Verifies username and password against database."""
    try:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and verify_password(password, user.password_hash):
                # Update last login
                user.last_login = datetime.utcnow()
                db.add(user)
                # Detach user representation for session
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "last_login": user.last_login
                }
    except Exception as e:
        st.error(f"Authentication error: {e}")
    return None


def init_auth_session():
    """Initializes authentication state in Streamlit session."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def login_user(user_dict: dict):
    """Sets session state to logged in."""
    st.session_state.authenticated = True
    st.session_state.user = user_dict


def logout_user():
    """Clears authentication session state."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()


def render_login_form():
    """Renders the login UI form."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2>🔐 ระบบจัดการหลังบ้าน (Admin Login)</h2>
            <p style="color: #666;">YOLO Tool Scanner & Dataset Management</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("ชื่อผู้ใช้ (Username)", placeholder="admin")
            password = st.text_input("รหัสผ่าน (Password)", type="password", placeholder="••••••••")
            submit_btn = st.form_submit_button("เข้าสู่ระบบ 🚀", use_container_width=True)

            if submit_btn:
                if not username or not password:
                    st.error("กรุณากรอกทั้งชื่อผู้ใช้และรหัสผ่าน")
                else:
                    user_info = authenticate(username.strip(), password.strip())
                    if user_info:
                        login_user(user_info)
                        st.success(f"ยินดีต้อนรับคุณ {user_info['username']} ({user_info['role']})")
                        st.rerun()
                    else:
                        st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง หรือไม่สามารถเชื่อมต่อฐานข้อมูลได้")
        
        st.info(f"💡 Default Account: `{ADMIN_DEFAULT_USER}` / `{ADMIN_DEFAULT_PASS}` (จาก `.env`)")
