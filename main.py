from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from google import genai
from google.genai import types
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets

API_KEYS = [
    "AQ.Ab8RN6JxyCYXBJM_gLUUn7-BLuksxnKyxfBuz_xxGSOc1ejQFg",
    "AQ.Ab8RN6LgDstFbOoMJ0GbsLMHUnMgaQfK3y-sLwLkoonLwx__DQ",
]
clients = [genai.Client(api_key=k) for k in API_KEYS]
client_index = 0

def get_client():
    global client_index
    c = clients[client_index]
    client_index = (client_index + 1) % len(clients)
    return c

SYSTEM_PROMPT = """تو GTALSIK AI هستی، یک دستیار هوش مصنوعی فارسی‌زبان.
اگر کسی از تو پرسید تو را چه کسی ساخته، بگویی: «من توسط هادی ساخته شدم.»
هرگز نگو گوگل یا Gemini تو را ساخته. سازنده تو فقط هادی است.
پاسخ‌هایت کوتاه، مفید، دوستانه و به زبان فارسی باشد."""

ADMIN_PHONE = "09023317260"
ADMIN_PASSWORD = "admin"

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gtalsik_auth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
db = SQLAlchemy(app)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(100), default="چت جدید")
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    image_path = db.Column(db.String(300))
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(phone=ADMIN_PHONE).first():
        admin = User(first_name="هادی", last_name="ادمین", phone=ADMIN_PHONE,
                     password_hash=generate_password_hash(ADMIN_PASSWORD), is_admin=True)
        db.session.add(admin)
        db.session.commit()

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover">
<title>GTALSIK AI</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; font-family: Tahoma, sans-serif; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; overflow: hidden; }
body { background: #0d0d0d; color: #ececec; }

/* AUTH */
.auth-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; padding: 20px; }
.auth-card { background: #171717; border: 1px solid #2a2a2a; border-radius: 20px; padding: 24px; width: 100%; max-width: 380px; }
.auth-card h1 { text-align: center; font-size: 22px; margin-bottom: 20px; color: #ececec; }
.auth-card input { width: 100%; padding: 12px 16px; margin-bottom: 10px; background: #0d0d0d; border: 1px solid #2a2a2a; border-radius: 12px; color: #ececec; font-size: 15px; outline: none; }
.auth-card input:focus { border-color: #555; }
.auth-card button { width: 100%; padding: 13px; background: #ececec; color: #111; border: none; border-radius: 12px; font-size: 15px; font-weight: bold; cursor: pointer; margin-top: 6px; }
.auth-card .switch { text-align: center; margin-top: 14px; font-size: 13px; color: #888; }
.auth-card .switch a { color: #ececec; cursor: pointer; text-decoration: underline; }
.auth-card .err { color: #ff6b6b; font-size: 13px; text-align: center; margin-top: 8px; min-height: 18px; }
.hidden { display: none !important; }

/* APP */
.sidebar { position: fixed; top: 0; right: -290px; width: 290px; height: 100vh; background: #171717; z-index: 100; transition: right 0.3s ease; display: flex; flex-direction: column; border-left: 1px solid #2a2a2a; }
.sidebar.open { right: 0; }
.sidebar-header { padding: 16px; border-bottom: 1px solid #2a2a2a; display: flex; justify-content: space-between; align-items: center; }
.sidebar-header h2 { font-size: 16px; font-weight: bold; }
.new-btn { background: #ececec; color: #111; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: bold; }
.user-info { padding: 12px 16px; border-bottom: 1px solid #2a2a2a; font-size: 13px; color: #aaa; }
.user-info b { color: #ececec; display: block; margin-bottom: 4px; font-size: 14px; }
.user-info .logout { color: #ff6b6b; cursor: pointer; margin-top: 8px; display: inline-block; }
.chat-list { flex: 1; overflow-y: auto; padding: 8px; }
.chat-item { padding: 12px; border-radius: 10px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; transition: background 0.15s; cursor: pointer; font-size: 14px; }
.chat-item:hover { background: #222; }
.chat-item.active { background: #2a2a2a; }
.chat-item span { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-actions { display: flex; gap: 4px; opacity: 0.6; }
.chat-actions button { background: none; border: none; color: #ececec; cursor: pointer; font-size: 13px; padding: 4px; }

.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 90; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
.overlay.show { opacity: 1; pointer-events: auto; }

.main { height: 100vh; display: flex; flex-direction: column; }
.header { background: #0d0d0d; padding: 14px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #2a2a2a; flex-shrink: 0; }
.menu-btn { background: none; border: none; color: #ececec; font-size: 22px; cursor: pointer; padding: 4px 8px; }
.header h1 { font-size: 16px; font-weight: bold; flex: 1; }
.admin-link { background: #ececec; color: #111; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: bold; cursor: pointer; border: none; }

.ad-banner { background: #2a2a2a; color: #ececec; padding: 10px 14px; font-size: 13px; border-bottom: 1px solid #333; text-align: center; }

.chat { flex: 1; overflow-y: auto; padding: 20px 16px 130px 16px; display: flex; flex-direction: column; gap: 16px; }
.msg-wrap { display: flex; flex-direction: column; max-width: 88%; }
.msg-wrap.user { align-self: flex-start; align-items: flex-start; }
.msg-wrap.bot { align-self: flex-end; align-items: flex-end; max-width: 95%; }
.msg { padding: 12px 16px; border-radius: 20px; line-height: 1.8; font-size: 15px; animation: fadeIn 0.3s ease; word-wrap: break-word; white-space: pre-wrap; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.user .msg { background: #2f2f2f; color: #ececec; border-bottom-right-radius: 6px; }
.bot .msg { background: transparent; color: #ececec; padding: 8px 4px; }
.msg img { max-width: 100%; border-radius: 12px; margin-top: 6px; display: block; }
.actions { display: flex; gap: 8px; margin-top: 4px; opacity: 0; transition: opacity 0.2s; }
.msg-wrap:hover .actions, .msg-wrap:focus-within .actions { opacity: 1; }
.actions button { background: #1f1f1f; color: #ccc; border: 1px solid #2a2a2a; padding: 6px 12px; border-radius: 14px; font-size: 12px; cursor: pointer; }

.typing { display: flex; gap: 4px; align-items: center; padding: 6px 4px; }
.typing span { width: 8px; height: 8px; background: #888; border-radius: 50%; animation: bounce 1.2s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-6px); } }

.input-area { position: fixed; bottom: 0; left: 0; right: 0; background: #0d0d0d; border-top: 1px solid #2a2a2a; padding: 10px 12px; padding-bottom: calc(10px + env(safe-area-inset-bottom)); z-index: 50; }
.preview-box { display: none; padding: 8px; background: #1a1a1a; border-radius: 12px; margin-bottom: 8px; position: relative; }
.preview-box.show { display: block; }
.preview-box img { max-height: 100px; border-radius: 8px; }
.preview-box .file-name { font-size: 13px; color: #ccc; }
.preview-box .close-preview { position: absolute; top: 4px; left: 4px; background: #333; color: #fff; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; }

.input-box { display: flex; gap: 8px; align-items: center; }
input[type=text] { flex: 1; padding: 12px 18px; border: 1px solid #2a2a2a; border-radius: 24px; outline: none; font-size: 16px; background: #1a1a1a; color: #ececec; }
input[type=text]::placeholder { color: #777; }
input[type=text]:focus { border-color: #555; background: #1f1f1f; }
.icon-btn { width: 46px; height: 46px; background: #1f1f1f; color: #ececec; border: none; border-radius: 50%; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.15s; }
.icon-btn:active { transform: scale(0.92); }
.send-btn { background: #ececec; color: #111; }
.send-btn:disabled { opacity: 0.4; }
.plus-menu { position: absolute; bottom: 70px; right: 12px; background: #1f1f1f; border: 1px solid #2a2a2a; border-radius: 14px; padding: 6px; display: none; flex-direction: column; gap: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
.plus-menu.show { display: flex; }
.plus-menu button { background: none; border: none; color: #ececec; padding: 10px 16px; border-radius: 10px; cursor: pointer; text-align: right; font-size: 14px; white-space: nowrap; }
.plus-menu button:active { background: #2a2a2a; }

.welcome { text-align: center; margin-top: 38%; color: #888; animation: fadeIn 0.6s ease; }
.welcome h2 { font-size: 24px; color: #ececec; margin-bottom: 12px; }
.welcome p { font-size: 14px; color: #999; }

/* ADMIN PANEL */
.admin-wrap { position: fixed; inset: 0; background: #0d0d0d; z-index: 200; overflow-y: auto; padding: 16px; display: none; }
.admin-wrap.show { display: block; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.admin-header h2 { font-size: 18px; }
.admin-close { background: #2a2a2a; color: #ececec; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
.admin-tabs { display: flex; gap: 6px; margin-bottom: 16px; overflow-x: auto; }
.admin-tab { background: #1a1a1a; color: #aaa; border: 1px solid #2a2a2a; padding: 8px 14px; border-radius: 10px; cursor: pointer; font-size: 13px; white-space: nowrap; }
.admin-tab.active { background: #ececec; color: #111; border-color: #ececec; }
.admin-section { display: none; }
.admin-section.show { display: block; }
.user-row { background: #171717; border: 1px solid #2a2a2a; border-radius: 12px; padding: 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.user-row .info { font-size: 13px; color: #ccc; }
.user-row .info b { color: #ececec; display: block; font-size: 14px; margin-bottom: 2px; }
.user-row .btns { display: flex; gap: 6px; }
.user-row button { border: none; padding: 6px 10px; border-radius: 8px; font-size: 12px; cursor: pointer; color: #fff; }
.btn-block { background: #d97706; }
.btn-unblock { background: #16a34a; }
.btn-kick { background: #dc2626; }
.btn-del { background: #7f1d1d; }
.ad-form { background: #171717; border: 1px solid #2a2a2a; border-radius: 12px; padding: 14px; margin-bottom: 12px; }
.ad-form textarea { width: 100%; padding: 12px; background: #0d0d0d; border: 1px solid #2a2a2a; border-radius: 10px; color: #ececec; font-size: 14px; min-height: 80px; outline: none; resize: vertical; font-family: Tahoma; }
.ad-form button { margin-top: 10px; background: #ececec; color: #111; border: none; padding: 10px 18px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 14px; }
.ad-item { background: #171717; border: 1px solid #2a2a2a; border-radius: 10px; padding: 10px; margin-bottom: 6px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
.ad-item button { background: #7f1d1d; color: #fff; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; }
</style>
</head>
<body>

<!-- AUTH -->
<div class="auth-wrap" id="authWrap">
    <div class="auth-card">
        <h1>GTALSIK AI</h1>

        <div id="loginForm">
            <input type="text" id="loginPhone" placeholder="شماره موبایل">
            <input type="password" id="loginPass" placeholder="رمز عبور">
            <button onclick="doLogin()">ورود</button>
            <div class="switch">حساب نداری؟ <a onclick="showTab('register')">ثبت‌نام کن</a></div>
        </div>

        <div id="registerForm" class="hidden">
            <input type="text" id="regFirst" placeholder="نام">
            <input type="text" id="regLast" placeholder="نام خانوادگی">
            <input type="text" id="regPhone" placeholder="شماره موبایل">
            <input type="password" id="regPass" placeholder="رمز عبور">
            <input type="password" id="regPass2" placeholder="تکرار رمز عبور">
            <button onclick="doRegister()">ثبت‌نام</button>
            <div class="switch">حساب داری؟ <a onclick="showTab('login')">وارد شو</a></div>
        </div>

        <div class="err" id="authErr"></div>
    </div>
</div>

<!-- APP -->
<div id="appWrap" class="hidden">
    <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>

    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>GTALSIK AI</h2>
            <button class="new-btn" onclick="newChat()">+ جدید</button>
        </div>
        <div class="user-info" id="userInfo"></div>
        <div class="chat-list" id="chatList"></div>
    </div>

    <div class="main">
        <div class="header">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <h1>GTALSIK AI</h1>
            <button class="admin-link hidden" id="adminBtn" onclick="openAdmin()">پنل مدیریت</button>
        </div>
        <div class="ad-banner hidden" id="adBanner"></div>
        <div class="chat" id="chat">
            <div class="welcome" id="welcome">
                <h2>سلام 👋</h2>
                <p>چطور می‌تونم کمکت کنم؟</p>
            </div>
        </div>
    </div>

    <div class="input-area">
        <div class="preview-box" id="previewBox">
            <button class="close-preview" onclick="clearPreview()">✕</button>
            <div id="previewContent"></div>
        </div>
        <div class="input-box">
            <button class="icon-btn" onclick="togglePlus()">+</button>
            <input type="text" id="msg" placeholder="پیام خود را بنویسید..." autocomplete="off">
            <button class="icon-btn send-btn" id="sendBtn" onclick="send()">➤</button>
        </div>
        <div class="plus-menu" id="plusMenu">
            <button onclick="pickImage()">🖼 ارسال عکس</button>
            <button onclick="pickFile()">📄 ارسال فایل</button>
            <button onclick="askImage()">🎨 ساخت عکس</button>
        </div>
    </div>

    <input type="file" id="imageInput" accept="image/*" style="display:none">
    <input type="file" id="fileInput" style="display:none">
</div>

<!-- ADMIN PANEL -->
<div class="admin-wrap" id="adminWrap">
    <div class="admin-header">
        <h2>پنل مدیریت</h2>
        <button class="admin-close" onclick="closeAdmin()">بستن</button>
    </div>
    <div class="admin-tabs">
        <div class="admin-tab active" onclick="showAdminTab('users', this)">کاربران</div>
        <div class="admin-tab" onclick="showAdminTab('ads', this)">تبلیغات</div>
    </div>

    <div class="admin-section show" id="sec-users">
        <div id="usersList"></div>
    </div>

    <div class="admin-section" id="sec-ads">
        <div class="ad-form">
            <textarea id="adText" placeholder="متن تبلیغ..."></textarea>
            <button onclick="sendAd()">ارسال به همه</button>
        </div>
        <div id="adsList"></div>
    </div>
</div>

<script>
let currentChatId = null;
let selectedFile = null;
let isAdmin = false;

function showTab(tab) {
    document.getElementById('loginForm').classList.toggle('hidden', tab !== 'login');
    document.getElementById('registerForm').classList.toggle('hidden', tab !== 'register');
    document.getElementById('authErr').innerText = '';
}

async function doLogin() {
    const phone = document.getElementById('loginPhone').value.trim();
    const pass = document.getElementById('loginPass').value;
    if (!phone || !pass) { document.getElementById('authErr').innerText = 'همه فیلدها را پر کن'; return; }
    const res = await fetch('/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({phone, password: pass})
    });
    const data = await res.json();
    if (data.ok) {
        startApp(data);
    } else {
        document.getElementById('authErr').innerText = data.error || 'خطا';
    }
}

async function doRegister() {
    const f = document.getElementById('regFirst').value.trim();
    const l = document.getElementById('regLast').value.trim();
    const p = document.getElementById('regPhone').value.trim();
    const pw = document.getElementById('regPass').value;
    const pw2 = document.getElementById('regPass2').value;
    if (!f || !l || !p || !pw) { document.getElementById('authErr').innerText = 'همه فیلدها را پر کن'; return; }
    if (pw !== pw2) { document.getElementById('authErr').innerText = 'رمزها یکسان نیستند'; return; }
    const res = await fetch('/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({first_name: f, last_name: l, phone: p, password: pw})
    });
    const data = await res.json();
    if (data.ok) {
        startApp(data);
    } else {
        document.getElementById('authErr').innerText = data.error || 'خطا';
    }
}

function startApp(data) {
    isAdmin = data.is_admin;
    document.getElementById('authWrap').classList.add('hidden');
    document.getElementById('appWrap').classList.remove('hidden');
    document.getElementById('userInfo').innerHTML = '<b>' + data.name + '</b>' + data.phone + '<br><span class="logout" onclick="logout()">خروج از حساب</span>';
    if (isAdmin) {
        document.getElementById('adminBtn').classList.remove('hidden');
        loadAdminUsers();
        loadAds();
    }
    loadAdBanner();
    loadChats();
}

async function logout() {
    await fetch('/logout', {method: 'POST'});
    location.reload();
}

async function loadAdBanner() {
    const res = await fetch('/ads/active');
    const ads = await res.json();
    const banner = document.getElementById('adBanner');
    if (ads.length > 0) {
        banner.innerText = '📢 ' + ads[0].text;
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('overlay').classList.toggle('show');
}

function togglePlus() {
    document.getElementById('plusMenu').classList.toggle('show');
}

function clearPreview() {
    selectedFile = null;
    document.getElementById('previewBox').classList.remove('show');
    document.getElementById('previewContent').innerHTML = '';
}

function pickImage() {
    document.getElementById('plusMenu').classList.remove('show');
    document.getElementById('imageInput').click();
}

function pickFile() {
    document.getElementById('plusMenu').classList.remove('show');
    document.getElementById('fileInput').click();
}

function askImage() {
    document.getElementById('plusMenu').classList.remove('show');
    document.getElementById('msg').value = 'یک عکس بساز: ';
    document.getElementById('msg').focus();
}

document.getElementById('imageInput').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    selectedFile = file;
    const url = URL.createObjectURL(file);
    document.getElementById('previewContent').innerHTML = '<img src="' + url + '">';
    document.getElementById('previewBox').classList.add('show');
});

document.getElementById('fileInput').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    selectedFile = file;
    document.getElementById('previewContent').innerHTML = '<div class="file-name">📄 ' + file.name + '</div>';
    document.getElementById('previewBox').classList.add('show');
});

async function loadChats() {
    const res = await fetch('/chats');
    if (res.status === 401) { location.reload(); return; }
    const chats = await res.json();
    const list = document.getElementById('chatList');
    list.innerHTML = '';
    chats.forEach(c => {
        const item = document.createElement('div');
        item.className = 'chat-item' + (c.id === currentChatId ? ' active' : '');
        item.innerHTML = '<span onclick="openChat(' + c.id + ')">' + c.title + '</span>' +
            '<div class="chat-actions">' +
            '<button onclick="event.stopPropagation(); renameChat(' + c.id + ', \'' + c.title.replace(/'/g, "\\'") + '\')">✎</button>' +
            '<button onclick="event.stopPropagation(); deleteChat(' + c.id + ')">🗑</button>' +
            '</div>';
        list.appendChild(item);
    });
}

async function newChat() {
    const res = await fetch('/chats', {method: 'POST'});
    const chat = await res.json();
    currentChatId = chat.id;
    document.getElementById('chat').innerHTML = '<div class="welcome"><h2>سلام 👋</h2><p>چطور می‌تونم کمکت کنم؟</p></div>';
    await loadChats();
    toggleSidebar();
}

async function openChat(id) {
    currentChatId = id;
    const res = await fetch('/chats/' + id);
    const messages = await res.json();
    const chat = document.getElementById('chat');
    chat.innerHTML = '';
    messages.forEach(m => addMsg(m.content, m.role === 'user' ? 'user' : 'bot', m.image_path, false));
    await loadChats();
    toggleSidebar();
}

async function deleteChat(id) {
    if (!confirm('این چت حذف شود؟')) return;
    await fetch('/chats/' + id, {method: 'DELETE'});
    if (currentChatId === id) {
        currentChatId = null;
        document.getElementById('chat').innerHTML = '<div class="welcome"><h2>سلام 👋</h2><p>چطور می‌تونم کمکت کنم؟</p></div>';
    }
    await loadChats();
}

async function renameChat(id, oldTitle) {
    const newTitle = prompt('اسم جدید:', oldTitle);
    if (!newTitle) return;
    await fetch('/chats/' + id, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: newTitle})
    });
    await loadChats();
}

async function send() {
    const input = document.getElementById('msg');
    const text = input.value.trim();
    if (!text && !selectedFile) return;

    if (!currentChatId) {
        const res = await fetch('/chats', {method: 'POST'});
        const chat = await res.json();
        currentChatId = chat.id;
    }

    const welcome = document.getElementById('welcome');
    if (welcome) welcome.remove();

    let imgUrl = null;
    if (selectedFile && selectedFile.type.startsWith('image/')) {
        imgUrl = URL.createObjectURL(selectedFile);
    }
    addMsg(text, 'user', imgUrl);

    input.value = '';
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    const loading = document.createElement('div');
    loading.className = 'msg-wrap bot';
    loading.innerHTML = '<div class="msg"><div class="typing"><span></span><span></span><span></span></div></div>';
    document.getElementById('chat').appendChild(loading);
    document.getElementById('chat').scrollTop = 999999;

    const formData = new FormData();
    formData.append('message', text);
    formData.append('chat_id', currentChatId);
    if (selectedFile) formData.append('file', selectedFile);

    try {
        const res = await fetch('/chat', {method: 'POST', body: formData});
        if (res.status === 403) {
            loading.remove();
            addMsg('حساب شما مسدود شده است', 'bot');
        } else {
            const data = await res.json();
            loading.remove();
            addMsg(data.reply, 'bot', data.image_url);
        }
    } catch (e) {
        loading.remove();
        addMsg('خطا در ارتباط', 'bot');
    }

    clearPreview();
    sendBtn.disabled = false;
    document.getElementById('chat').scrollTop = 999999;
    await loadChats();
}

function addMsg(text, type, imageUrl, animate = true) {
    const wrap = document.createElement('div');
    wrap.className = 'msg-wrap ' + type;
    const msg = document.createElement('div');
    msg.className = 'msg';
    if (!animate) msg.style.animation = 'none';
    if (text) {
        const txt = document.createElement('div');
        txt.innerText = text;
        msg.appendChild(txt);
    }
    if (imageUrl) {
        const img = document.createElement('img');
        img.src = imageUrl;
        msg.appendChild(img);
    }
    wrap.appendChild(msg);
    const actions = document.createElement('div');
    actions.className = 'actions';
    if (text) {
        const copyBtn = document.createElement('button');
        copyBtn.innerText = '📋 کپی';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(text);
            copyBtn.innerText = '✓ کپی شد';
            setTimeout(() => copyBtn.innerText = '📋 کپی', 1500);
        };
        actions.appendChild(copyBtn);
    }
    if (imageUrl) {
        const dlBtn = document.createElement('button');
        dlBtn.innerText = '⬇ دانلود';
        dlBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = imageUrl;
            a.download = 'gtalsik.png';
            a.click();
        };
        actions.appendChild(dlBtn);
    }
    wrap.appendChild(actions);
    document.getElementById('chat').appendChild(wrap);
    document.getElementById('chat').scrollTop = 999999;
    return wrap;
}

document.getElementById('msg').addEventListener('keypress', e => {
    if (e.key === 'Enter') send();
});

document.addEventListener('click', e => {
    const menu = document.getElementById('plusMenu');
    if (menu.classList.contains('show') && !e.target.closest('.input-area')) {
        menu.classList.remove('show');
    }
});

/* ADMIN */
function openAdmin() {
    document.getElementById('adminWrap').classList.add('show');
}

function closeAdmin() {
    document.getElementById('adminWrap').classList.remove('show');
}

function showAdminTab(name, el) {
    document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('show'));
    document.getElementById('sec-' + name).classList.add('show');
}

async function loadAdminUsers() {
    const res = await fetch('/admin/users');
    const users = await res.json();
    const list = document.getElementById('usersList');
    list.innerHTML = '';
    users.forEach(u => {
        const row = document.createElement('div');
        row.className = 'user-row';
        let btns = '';
        if (!u.is_admin) {
            if (u.is_blocked) {
                btns += '<button class="btn-unblock" onclick="adminAction(\'/admin/unblock/' + u.id + '\')">آنبلاک</button>';
            } else {
                btns += '<button class="btn-block" onclick="adminAction(\'/admin/block/' + u.id + '\')">مسدود</button>';
            }
            btns += '<button class="btn-del" onclick="if(confirm(\'حذف شود؟\')) adminAction(\'/admin/delete/' + u.id + '\')">حذف</button>';
        }
        row.innerHTML = '<div class="info"><b>' + u.name + '</b>' + u.phone + (u.is_blocked ? ' <span style="color:#ff6b6b">[مسدود]</span>' : '') + (u.is_admin ? ' <span style="color:#16a34a">[ادمین]</span>' : '') + '</div>' +
            '<div class="btns">' + btns + '</div>';
        list.appendChild(row);
    });
}

async function adminAction(url) {
    await fetch(url, {method: 'POST'});
    loadAdminUsers();
}

async function sendAd() {
    const text = document.getElementById('adText').value.trim();
    if (!text) return;
    await fetch('/admin/ads', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text})
    });
    document.getElementById('adText').value = '';
    loadAds();
}

async function loadAds() {
    const res = await fetch('/admin/ads');
    const ads = await res.json();
    const list = document.getElementById('adsList');
    list.innerHTML = '';
    ads.forEach(a => {
        const item = document.createElement('div');
        item.className = 'ad-item';
        item.innerHTML = '<span>' + a.text + '</span><button onclick="delAd(' + a.id + ')">حذف</button>';
        list.appendChild(item);
    });
}

async function delAd(id) {
    await fetch('/admin/ads/' + id, {method: 'DELETE'});
    loadAds();
}
</script>
</body>
</html>
"""

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

@app.route('/')
def home():
    return HTML_PAGE

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    f = data.get('first_name', '').strip()
    l = data.get('last_name', '').strip()
    p = data.get('phone', '').strip()
    pw = data.get('password', '')
    if not f or not l or not p or not pw:
        return jsonify({'ok': False, 'error': 'همه فیلدها الزامی است'})
    if User.query.filter_by(phone=p).first():
        return jsonify({'ok': False, 'error': 'این شماره قبلاً ثبت شده'})
    u = User(first_name=f, last_name=l, phone=p, password_hash=generate_password_hash(pw))
    db.session.add(u)
    db.session.commit()
    session['user_id'] = u.id
    return jsonify({'ok': True, 'name': f + ' ' + l, 'phone': p, 'is_admin': False})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    p = data.get('phone', '').strip()
    pw = data.get('password', '')
    u = User.query.filter_by(phone=p).first()
    if not u or not check_password_hash(u.password_hash, pw):
        return jsonify({'ok': False, 'error': 'شماره یا رمز اشتباه است'})
    if u.is_blocked and not u.is_admin:
        return jsonify({'ok': False, 'error': 'حساب شما مسدود شده است'})
    session['user_id'] = u.id
    return jsonify({'ok': True, 'name': u.first_name + ' ' + u.last_name, 'phone': u.phone, 'is_admin': u.is_admin})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/chats', methods=['GET'])
def get_chats():
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    chats = Chat.query.filter_by(user_id=u.id).order_by(Chat.created.desc()).all()
    return jsonify([{'id': c.id, 'title': c.title} for c in chats])

@app.route('/chats', methods=['POST'])
def create_chat():
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    chat = Chat(user_id=u.id, title='چت جدید')
    db.session.add(chat)
    db.session.commit()
    return jsonify({'id': chat.id, 'title': chat.title})

@app.route('/chats/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    c = Chat.query.filter_by(id=chat_id, user_id=u.id).first()
    if not c: return jsonify({'error': 'not found'}), 404
    msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.created).all()
    return jsonify([{'role': m.role, 'content': m.content, 'image_path': m.image_path} for m in msgs])

@app.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    c = Chat.query.filter_by(id=chat_id, user_id=u.id).first()
    if not c: return jsonify({'error': 'not found'}), 404
    Message.query.filter_by(chat_id=chat_id).delete()
    Chat.query.filter_by(id=chat_id).delete()
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/chats/<int:chat_id>', methods=['PUT'])
def rename_chat(chat_id):
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    c = Chat.query.filter_by(id=chat_id, user_id=u.id).first()
    if not c: return jsonify({'error': 'not found'}), 404
    data = request.get_json()
    c.title = data.get('title', c.title)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/chat', methods=['POST'])
def chat():
    u = current_user()
    if not u: return jsonify({'error': 'auth'}), 401
    if u.is_blocked and not u.is_admin:
        return jsonify({'reply': 'حساب شما مسدود شده است', 'image_url': None}), 403

    msg = request.form.get('message', '')
    chat_id = request.form.get('chat_id')
    file = request.files.get('file')

    c = Chat.query.filter_by(id=chat_id, user_id=u.id).first()
    if not c: return jsonify({'error': 'not found'}), 404

    saved_path = None
    if file:
        filename = str(int(datetime.utcnow().timestamp())) + '_' + file.filename
        saved_path = os.path.join(UPLOAD_DIR, filename)
        file.save(saved_path)

    user_msg = Message(chat_id=chat_id, role='user', content=msg, image_path=saved_path if saved_path and file.content_type.startswith('image/') else None)
    db.session.add(user_msg)

    if c.title == 'چت جدید':
        title_text = msg if msg else (file.filename if file else 'چت جدید')
        c.title = title_text[:30] + ('...' if len(title_text) > 30 else '')

    db.session.commit()

    is_image_request = any(k in msg for k in ['عکس بساز', 'تصویر بساز', 'بکش', 'نقاشی', 'ایمیج', 'image', 'photo'])

    try:
        if is_image_request:
            response = get_client().models.generate_content(model="gemini-3-pro-image", contents=msg)
        else:
            history = Message.query.filter_by(chat_id=chat_id).order_by(Message.created).all()
            contents = []
            for m in history:
                parts = [{'text': m.content or ''}]
                if m.image_path and os.path.exists(m.image_path):
                    with open(m.image_path, 'rb') as f:
                        img_bytes = f.read()
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type='image/png'))
                contents.append({'role': 'user' if m.role == 'user' else 'model', 'parts': parts})
            response = get_client().models.generate_content(
                model="gemini-3.5-flash",
                contents=contents,
                config={'system_instruction': SYSTEM_PROMPT}
            )

        reply_text = ''
        reply_image_path = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    reply_text += part.text
                if hasattr(part, 'inline_data') and part.inline_data:
                    img_filename = 'gen_' + str(int(datetime.utcnow().timestamp())) + '.png'
                    reply_image_path = os.path.join(UPLOAD_DIR, img_filename)
                    with open(reply_image_path, 'wb') as f:
                        f.write(part.inline_data.data)
        if not reply_text:
            reply_text = 'بفرما عکست' if reply_image_path else '(پاسخی دریافت نشد)'

        bot_msg = Message(chat_id=chat_id, role='bot', content=reply_text, image_path=reply_image_path)
        db.session.add(bot_msg)
        db.session.commit()

        return jsonify({
            'reply': reply_text,
            'image_url': '/uploads/' + os.path.basename(reply_image_path) if reply_image_path else None
        })
    except Exception as e:
        return jsonify({'reply': 'خطا: ' + str(e), 'image_url': None})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/admin/users')
def admin_users():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    users = User.query.order_by(User.created.desc()).all()
    return jsonify([{'id': x.id, 'name': x.first_name + ' ' + x.last_name, 'phone': x.phone, 'is_admin': x.is_admin, 'is_blocked': x.is_blocked} for x in users])

@app.route('/admin/block/<int:uid>', methods=['POST'])
def admin_block(uid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    x = User.query.get(uid)
    if x and not x.is_admin:
        x.is_blocked = True
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/unblock/<int:uid>', methods=['POST'])
def admin_unblock(uid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    x = User.query.get(uid)
    if x:
        x.is_blocked = False
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/delete/<int:uid>', methods=['POST'])
def admin_delete(uid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    x = User.query.get(uid)
    if x and not x.is_admin:
        for c in Chat.query.filter_by(user_id=uid).all():
            Message.query.filter_by(chat_id=c.id).delete()
            db.session.delete(c)
        db.session.delete(x)
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/ads', methods=['GET'])
def admin_ads_get():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    ads = Ad.query.order_by(Ad.created.desc()).all()
    return jsonify([{'id': a.id, 'text': a.text} for a in ads])

@app.route('/admin/ads', methods=['POST'])
def admin_ads_post():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    data = request.get_json()
    ad = Ad(text=data.get('text', ''))
    db.session.add(ad)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/ads/<int:aid>', methods=['DELETE'])
def admin_ads_del(aid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'forbidden'}), 403
    Ad.query.filter_by(id=aid).delete()
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/ads/active')
def ads_active():
    ads = Ad.query.filter_by(active=True).order_by(Ad.created.desc()).limit(1).all()
    return jsonify([{'id': a.id, 'text': a.text} for a in ads])

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
