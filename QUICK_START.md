# KAZUMEE QUICK START GUIDE

## 🚀 LOCAL DEVELOPMENT SETUP

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL (or SQLite for testing)
- Git

### 1. Start Frontend Dev Server

```bash
cd frontend/web
npm install  # Only if node_modules missing
npm run dev
```

**Expected Output:**
```
Vite dev server running at:
  > Local: http://localhost:5173/
```

**Test:** Open `http://localhost:5173` in browser

---

### 2. Start Backend Dev Server

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

**Expected Output:**
```
Uvicorn running on http://127.0.0.1:8000
```

**Test:** Visit `http://127.0.0.1:8000/health`

---

### 3. Environment Configuration

Create `.env` files:

**Frontend: `frontend/web/.env.local`**
```env
VITE_API_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000/ws
```

**Backend: `.env`**
```env
DATABASE_URL=sqlite:///./test.db  # or postgresql://...
GROQ_API_KEY=your_groq_key_here
TWITCH_CLIENT_ID=your_twitch_id
TWITCH_CLIENT_SECRET=your_twitch_secret
YOUTUBE_API_KEY=your_youtube_key
JWT_SECRET=your_secret_key_change_me
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 🧪 TESTING FLOWS

### Test 1: New Streamer Registration

**Steps:**
1. Open `http://localhost:5173`
2. Click "Start Free" button
3. Verify redirected to `/auth`
4. Fill email: `streamer@test.com`, password: `password123`
5. Select "Streamer" role
6. Click "Create Account"

**Expected Results:**
- ✅ Email validated (not empty, trimmed)
- ✅ Password validated (8+ chars)
- ✅ Success toast appears
- ✅ Redirected to `/onboarding`
- ✅ See 4-step onboarding

**Onboarding Steps:**
1. Enter display name, select platform
2. Enter OBS password, test connection (will fail without OBS, that's OK)
3. Record voice fingerprint (can skip)
4. Assign scene aliases (can skip)
5. Click "Go to Dashboard"

**Expected Results:**
- ✅ Redirected to `/`
- ✅ See streamer dashboard
- ✅ See onboarding banner (if not completed)

---

### Test 2: New Viewer Registration

**Steps:**
1. Open `http://localhost:5173`
2. Scroll to "For Viewers" section
3. Click "Watch as a Viewer"
4. Verify redirected to `/auth`
5. Fill email: `viewer@test.com`, password: `password123`
6. Verify "Viewer" is selected (default)
7. Click "Create Account"

**Expected Results:**
- ✅ Viewer role selected by default
- ✅ Success toast appears
- ✅ Redirected to `/viewer`
- ✅ See viewer page with streamer options

---

### Test 3: Streamer Login

**Steps:**
1. Open `http://localhost:5173`
2. Click "Log In" (or "Start Free" then click "Sign In")
3. Enter: `streamer@test.com`, `password123`
4. Click "Sign In"

**Expected Results:**
- ✅ Success message
- ✅ Redirected to `/` (dashboard)
- ✅ See streamer dashboard with controls
- ✅ See onboarding banner if applicable

---

### Test 4: Viewer Login

**Steps:**
1. Open `http://localhost:5173/auth`
2. Enter: `viewer@test.com`, `password123`
3. Click "Sign In"

**Expected Results:**
- ✅ Success message
- ✅ Redirected to `/viewer`
- ✅ See viewer page

---

### Test 5: Role Switching

**Steps (from auth page with existing user):**
1. If logged in, see "Signed in as: [email]"
2. See "Switch Role" buttons
3. Click "Streamer" if currently viewer, or vice versa

**Expected Results:**
- ✅ Role updated on backend
- ✅ Redirected to appropriate page (`/` for streamer, `/viewer` for viewer)

---

### Test 6: Landing Page Navigation

**Test All Buttons:**
- Navbar "Start Free" → `/auth` ✅
- Navbar "Log In" → `/auth` ✅
- Hero "Start Free" → `/auth` ✅
- Hero "Watch Demo" → `/auth` ✅
- ViewerSection "Watch as a Viewer" → `/auth` ✅
- ViewerSection "See It In Action" → YouTube (external) ✅
- Pricing cards → `/auth` ✅
- CTA "Start Your Journey" → `/auth` ✅

**Test Navigation Links:**
- Click "Features" → scroll to Features section ✅
- Click "How It Works" → scroll to HowItWorks ✅
- Click "For Viewers" → scroll to ViewerSection ✅
- Click "Pricing" → scroll to PricingSection ✅

**Test Social Links:**
- Twitter icon → opens twitter.com/kazumee in new tab ✅
- Discord icon → opens discord.gg/kazumee in new tab ✅
- YouTube icon → opens youtube.com/@kazumee in new tab ✅

---

### Test 7: Authorization & Routing

**Test Streamer Access:**
1. Login as streamer
2. Try to visit `/viewer` → should redirect to `/`
3. Try to visit `/auth` → should show auth page (not redirect)

**Test Viewer Access:**
1. Login as viewer
2. Try to visit `/stream-health` → should redirect to `/viewer`
3. Try to visit `/auth` → should show auth page (not redirect)

**Test Unauthenticated Access:**
1. Clear auth token: `localStorage.removeItem('kazumi_auth_token')`
2. Visit `/stream-health` → should redirect to `/auth`
3. Visit `/viewer` → should allow (no auth required)
4. Visit `/` → should show landing page

---

### Test 8: Error Handling

**Test Empty Email:**
1. Go to `/auth`
2. Leave email empty
3. Enter password
4. Click sign in
5. Expected: Error toast "Email is required" ✅

**Test Short Password:**
1. Go to `/auth` register mode
2. Enter email
3. Enter password: `pass`
4. Click "Create Account"
5. Expected: Error toast "Password must be at least 8 characters" ✅

**Test Invalid Credentials:**
1. Go to `/auth` login
2. Enter: `nonexistent@test.com`, `password123`
3. Click "Sign In"
4. Expected: Error message "Invalid credentials" or similar ✅

**Test Network Error:**
1. Stop backend server
2. Try to login
3. Expected: Error message "Could not reach backend" ✅

---

### Test 9: Session Persistence

**Test Remember Me:**
1. Login with "Remember me" checked
2. Close browser
3. Reopen site
4. Expected: Still logged in ✅

**Test Session Expiration:**
1. Clear auth token: `localStorage.clear()`
2. Visit `/stream-health`
3. Expected: Redirected to `/auth` with "Session expired" message ✅

---

### Test 10: Responsive Design

**Test on Different Screen Sizes:**

**Mobile (375px):**
- Landing page stacks vertically ✅
- Buttons are readable ✅
- Hero image hidden (lg:block) ✅
- Navigation responsive ✅

**Tablet (768px):**
- Two-column layout where applicable ✅
- Grid adjusts properly ✅
- All interactive elements accessible ✅

**Desktop (1920px):**
- Full layout renders ✅
- Hero image visible ✅
- Cards display in grids ✅
- Hover effects work ✅

---

## 🐛 DEBUGGING TIPS

### Check Browser Console
Open DevTools (F12) → Console tab
- ✅ No red errors
- ⚠️ Warnings are OK (sourcemap issues are known)
- Check for API call errors

### Check Network Requests
Open DevTools → Network tab
- Watch API calls to `/auth/register`, `/auth/login`, `/auth/me`
- Verify status codes (200, 400, 401, etc.)
- Check response JSON

### Check Backend Logs
Terminal running backend server:
- Look for database errors
- Look for auth errors
- Look for API response codes

### Check Frontend Logs
Browser console:
- Look for React errors
- Look for API call logs
- Look for authentication state logs

---

## 📊 QUICK CHECKLIST

After making changes and before committing:

### Code Quality
- [ ] No console errors
- [ ] No console warnings (except sourcemap)
- [ ] No broken links
- [ ] All buttons work
- [ ] All forms validate

### Features
- [ ] Landing page displays correctly
- [ ] All landing buttons go to `/auth`
- [ ] Auth page works (login/register)
- [ ] Onboarding loads correctly
- [ ] Dashboard loads for streamers
- [ ] Viewer page loads for viewers

### Authorization
- [ ] Unauthenticated users see landing at `/`
- [ ] Authenticated streamers see dashboard at `/`
- [ ] Authenticated viewers go to `/viewer`
- [ ] Protected routes redirect to `/auth`

### Mobile
- [ ] Landing page responsive
- [ ] Auth page responsive
- [ ] Onboarding responsive
- [ ] Dashboard responsive

### Performance
- [ ] Page load time < 3 seconds
- [ ] No jank on interactions
- [ ] Images load properly
- [ ] No memory leaks

---

## 🚢 DEPLOYMENT CHECKLIST

Before deploying to production:

### Code
- [ ] All tests passing
- [ ] No console errors
- [ ] No breaking changes
- [ ] Documentation updated
- [ ] Environment variables set

### Frontend
- [ ] Build succeeds: `npm run build`
- [ ] No build warnings (except sourcemap)
- [ ] Assets optimized (images compressed)
- [ ] CSS minified
- [ ] JavaScript minified

### Backend
- [ ] Imports work: `python -c "import backend.main"`
- [ ] Database migrations run
- [ ] Environment variables configured
- [ ] API endpoints tested
- [ ] Rate limiting configured

### Infrastructure
- [ ] Database backups enabled
- [ ] Error tracking configured (Sentry)
- [ ] Monitoring enabled
- [ ] CDN configured
- [ ] HTTPS/SSL enabled
- [ ] CORS configured

### Security
- [ ] Social links updated with real URLs
- [ ] API keys secured (not in repo)
- [ ] Database password changed
- [ ] JWT secret changed
- [ ] CORS origins updated
- [ ] Rate limits configured

### Documentation
- [ ] README updated
- [ ] API docs updated
- [ ] Deployment guide created
- [ ] Support contacts provided
- [ ] Change log updated

---

## 🎯 SUCCESS CRITERIA

Your implementation is successful when:

✅ All landing page buttons navigate to `/auth`
✅ New streamers can register and see onboarding
✅ New viewers can register and see viewer page
✅ Returning users see correct dashboards
✅ Unauthenticated users see landing page
✅ Protected routes require authentication
✅ Error messages are clear and helpful
✅ Mobile layout is responsive
✅ Build completes without errors
✅ Backend imports successfully

---

## 📞 GETTING HELP

If you encounter issues:

1. **Check the logs** - Browser console and backend terminal
2. **Check network requests** - DevTools Network tab
3. **Clear cache** - `localStorage.clear()` + browser cache
4. **Restart servers** - Kill and restart frontend and backend
5. **Review documentation** - Check IMPLEMENTATION_GUIDE.md
6. **Check git diff** - Verify all changes are present

---

**Ready to start testing? 🚀**

Run these commands:

```bash
# Terminal 1: Frontend
cd frontend/web && npm run dev

# Terminal 2: Backend
cd . && python -m uvicorn backend.main:app --reload

# Terminal 3: Open browser
# http://localhost:5173
```

Then follow the testing flows above!

---

**Last Updated:** 2026-07-09
**Status:** ✅ READY FOR TESTING
