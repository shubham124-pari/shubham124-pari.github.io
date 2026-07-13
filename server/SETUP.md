# Backend Setup — Complete

## 1. MySQL database banao
```bash
mysql -u root -p < server/database/schema.sql
```
Fresh install par ye seedha latest schema (users, projects, chatbot_history,
contact_messages — role/ban/reset-token/message-linking sab included) bana
dega.

Agar tumne pehle purani schema.sql se database already bana liya tha, to
migrations chalao (order me):
```bash
mysql -u root -p shubham_portfolio < server/database/migrations/002_add_resume_certificate.sql
mysql -u root -p shubham_portfolio < server/database/migrations/003_add_contact_subject.sql
mysql -u root -p shubham_portfolio < server/database/migrations/004_add_admin_and_message_linking.sql
mysql -u root -p shubham_portfolio < server/database/migrations/005_add_chat_and_presence.sql
mysql -u root -p shubham_portfolio < server/database/migrations/006_add_dashboard_extras.sql
mysql -u root -p shubham_portfolio < server/database/migrations/007_add_social_features.sql
```

## 2. `.env` file fill karo
`server/.env` already ban chuki hai. Zaroori values:
```
DB_PASSWORD=apna_mysql_password
JWT_SECRET_KEY=koi_lambi_random_string
ADMIN_EMAIL=apna_email@example.com     # ye email jab signup karega, admin ban jayega
```
Optional (AI chatbot, password reset email, contact-form-to-inbox) — README
me detail hai.

Password reset email ke liye **Brevo** recommended hai (free, aur Render
free tier pe bhi kaam karta hai — SMTP wahan blocked hai). `.env` me
`BREVO_API_KEY` aur `BREVO_SENDER_EMAIL` set karo — free account
[app.brevo.com](https://app.brevo.com) par banao, API key generate karo,
apna sender email verify karo.

⚠️ `.env` ko kabhi GitHub par push mat karna — `.gitignore` already isko
exclude karta hai.

## 3. Dependencies install karo
```bash
cd server
pip install -r requirements.txt
```

## 4. Server chalao
```bash
python app.py
```
Server `http://127.0.0.1:5000` par chalega.

## 5. Apna admin account banao
1. Pehle `.env` me `ADMIN_EMAIL=tera_email@example.com` set karo.
2. Server (re)start karo.
3. Site par usi email se normal signup karo — ye account automatically
   `role = admin` ban jayega.
4. Ab `/admin.html` par jaake usi email/password se sign in karo.

## Kya-kya ban chuka hai (poora backend)
- **Auth**: signup, login, JWT, forgot-password + reset-password (email link,
  30-min expiry), `/api/auth/me`
- **User Dashboard** (`/dashboard.html`): profile edit (name/bio),
  profile photo + cover photo upload (real image validation + EXIF
  stripping), resume/certificate upload & replace, projects full CRUD,
  skills (add/edit/delete with a level), education & experience
  timelines (full CRUD), notification center (chat/account notifications,
  mark read), activity timeline (login, profile edits, uploads, project
  changes, ...), personal dashboard analytics (project/skill/chat/AI-chat
  counts, unread notifications, profile completeness), theme setting
  (dark/light), privacy setting (public/private profile), notification
  preferences (email / chat), password change, delete account —
  Professional Glassmorphism UI throughout (`assets/css/style.css`,
  the "DASHBOARD" section at the bottom)
- **Contact form**: `/api/contact` — MySQL me save + (optional) Web3Forms se
  tere inbox me email. Logged-in user bheje to uske dashboard me bhi dikhta
  hai (`/api/contact/mine`)
- **AI Chatbot**: `/api/chatbot/ask` — Gemini ya OpenAI (`.env` me
  `AI_PROVIDER` se choose karo), sign-in ke bina bhi kaam karta hai,
  history `chatbot_history` table me save hoti hai. Ab **multilingual**
  hai (jo bhi language me poochoge, usi me jawab milega), aur
  **programming / cybersecurity / career / resume / portfolio** — panch
  tarah ke sawalon ka jawab deta hai, Markdown + code-highlighting ke
  saath, aur pichle 6 messages yaad rakhta hai (follow-up questions ke
  liye).
- **Private Chat** (`/chat.html`): sign-in members ke beech real-time
  one-to-one messaging — `/api/chat/*` (REST: conversation list, history,
  search, delete) + Socket.IO (`server/sockets.py` — typing indicator,
  online/offline status, instant delivery, read receipts). Image aur
  document sharing bhi chalta hai (`/api/user/upload/chat_image` aur
  `/upload/chat_document`).
- **Admin Panel**: `/api/admin/*` — sare users dekhna/ban/delete karna, sare
  contact messages dekhna/status badalna/delete karna, analytics (total
  users, signups/day, messages, chatbot usage)
- **Security**: password hashing (Werkzeug/scrypt), JWT auth, admin-only
  routes (role DB se fresh check hoti hai, JWT se nahi), parameterized SQL
  (SQL-injection proof), input validation har route par, rate limiting
  (auth/contact/chatbot), CORS sirf tere frontend origin ke liye, upload
  file-type/size/real-image verification

## Frontend chalane ka tareeka (zaroori)

Frontend HTML files ko seedhe double-click karke (`file://...`) mat kholna —
browser CORS block kar dega. Iske bajaye:
- VS Code me "Live Server" extension se `index.html` open karo (default port 5500), YA
- Terminal me `python -m http.server 5500` chala ke `http://127.0.0.1:5500` par kholo

`server/.env` me `FRONTEND_ORIGIN=http://127.0.0.1:5500` already set hai — agar
tum koi aur port use karo to yahan bhi wahi port daal dena.

## Deployment (jab ready ho)
1. **Backend**: Render/Railway par deploy karo (Python service). Wahan pe
   `.env` ke sare variables environment variables ke roop me daalne honge
   (dashboard me). `DB_HOST` etc. ke liye ek managed MySQL (Railway/PlanetScale/
   Aiven free tier) use kar sakte ho.
2. **Frontend**: GitHub Pages par already hai. Bas `assets/js/*.js` files ke
   top me jo `SKP_API_BASE` / `*_API_BASE` constant hai, use apne deployed
   backend URL se replace karna mat bhoolna.
3. `server/.env` me `FRONTEND_ORIGIN` ko apne GitHub Pages URL se update karo
   (CORS ke liye), aur `FRONTEND_URL` ko bhi (reset-password email link ke
   liye).
