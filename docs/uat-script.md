# Brag Board — Family UAT Script
**URL:** https://brag.woodsandbryant.com  
**Date:** _______________  
**Tester Name:** _______________  
**Device / Browser:** _______________

Mark each test **PASS ✅** or **FAIL ❌**. If it fails, jot a quick note on what happened.

---

## Test 1 — Login

**Before you start:** Have your username and password ready.

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to https://brag.woodsandbryant.com | You see a login page | |
| 2 | Enter your username and password, tap **Sign In** | You land on the main board | |
| 3 | Your name and avatar appear in the top-right corner | Correct name and color shown | |

**Notes:** _______________

---

## Test 2 — Post a Text Brag

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On the main board, tap the text box that says *"I just did something awesome…"* | Keyboard appears, cursor in box | |
| 2 | Type something you did (e.g. "Washed all the dishes") | Text appears in the box | |
| 3 | Choose a category from the dropdown (e.g. 🍽️ Kitchen) | Category is selected | |
| 4 | Tap **🏆 Post Brag** | Your brag appears at the top of the feed | |
| 5 | Check the brag shows your name, category badge, and points (e.g. +3⭐) | All three visible | |

**Notes:** _______________

---

## Test 3 — Post a Brag with a Photo (Camera)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap the text box and write a short brag | Text entered | |
| 2 | Tap the **📸** button | A small menu pops up with two options | |
| 3 | Tap **📷 Take Photo** | Your camera opens | |
| 4 | Take a photo | Camera closes, you see a small preview of the photo below the text box | |
| 5 | Tap **🏆 Post Brag** | You briefly see ⏳, then the brag posts with your photo visible in the feed | |
| 6 | Tap the photo in the feed | Opens full size in a new tab | |

**Notes:** _______________

---

## Test 4 — Post a Brag with a Photo (Gallery)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Write a short brag in the text box | Text entered | |
| 2 | Tap **📸**, then tap **🖼️ Choose from Gallery** | Your photo library opens | |
| 3 | Pick an existing photo | Preview appears below the text box | |
| 4 | Tap **🏆 Post Brag** | Brag posts with the photo in the feed | |

**Notes:** _______________

---

## Test 5 — Remove a Photo Before Posting

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Write a brag and attach a photo (see Test 3 or 4) | Preview photo shown | |
| 2 | Tap **✕ remove** below the preview | Photo preview disappears, 📸 button resets | |
| 3 | Tap **🏆 Post Brag** | Brag posts without any photo | |

**Notes:** _______________

---

## Test 6 — React to a Brag

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Find any brag in the feed | Brag visible with reaction buttons (❤️ 🙌 🔥) | |
| 2 | Tap **❤️** | Button turns blue/highlighted, count goes up by 1 | |
| 3 | Tap **❤️** again | Reaction is removed, count goes back down | |
| 4 | Tap **🙌** on a brag someone else posted | Your name appears in the tooltip when you hover/hold | |

**Notes:** _______________

---

## Test 7 — Add a Wish

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On the main board, find the **🌠 Wish List** panel on the right (scroll down on phone) | Wish list visible | |
| 2 | Type a wish in the box (e.g. "Someone mow the backyard") | Text entered | |
| 3 | Tap **+ Add** | Your wish appears in the list with your name | |

**Notes:** _______________

---

## Test 8 — Claim a Wish

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Find an open wish in the Wish List | Wish shows with "✅ I did it!" button | |
| 2 | Choose a category from the small dropdown next to the button | Category selected | |
| 3 | Tap **✅ I did it!** | Wish moves to the "Wishes Granted" section; a new brag appears in your feed | |
| 4 | Check your points went up | ⭐ balance increases in the top bar | |

**Notes:** _______________

---

## Test 9 — View Your Profile & Badges

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap your name/avatar in the top-right corner | Opens your profile page | |
| 2 | Check your points balance and streak are shown | Both visible under your name | |
| 3 | Scroll to the Badges section | Earned badges are bright; unearned badges are greyed out | |
| 4 | Tap/hover an unearned badge | Tooltip shows what you need to do to earn it | |
| 5 | Edit your display name and tap **Save Name** | Name updates everywhere on the board | |

**Notes:** _______________

---

## Test 10 — Rewards Page

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap **🏆 Rewards** in the nav bar | Rewards page opens | |
| 2 | Check your points balance at the top | Matches what's shown on the main board | |
| 3 | View the leaderboard | All family members listed with balances | |
| 4 | If any rewards are listed, tap **Redeem** on one you can afford | Confirmation message appears: "Waiting for approval" | |

**Notes:** _______________

---

## Test 11 — Sign Out & Sign Back In

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap **Sign out** in the top-right | Redirected to login page | |
| 2 | Sign back in with your credentials | Back to the main board, still logged in as you | |
| 3 | Close the browser tab, reopen the site | Still logged in (session persists) | |

**Notes:** _______________

---

## Admin-Only Tests
*Skip these if you are not the admin.*

### Test 12 — Add/Edit User Email (Admin)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap ⚙️ **Settings** | Settings page opens | |
| 2 | Find a family member in the list | Email input shown below their name | |
| 3 | Enter or update their email and tap **Save** | "Email updated" confirmation shown | |

### Test 13 — Send Weekly Digest (Admin)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to ⚙️ **Settings**, scroll to the bottom | "📧 Weekly Digest" card visible | |
| 2 | Tap **Send Now** | "Weekly digest sent! ✉️" confirmation | |
| 3 | Check inbox for the digest email | Email received with leaderboard, streaks, and brags | |

---

## Summary

| Test | Description | Result |
|------|-------------|--------|
| 1 | Login | |
| 2 | Post text brag | |
| 3 | Post brag with camera photo | |
| 4 | Post brag from gallery | |
| 5 | Remove photo before posting | |
| 6 | React to a brag | |
| 7 | Add a wish | |
| 8 | Claim a wish | |
| 9 | Profile & badges | |
| 10 | Rewards page | |
| 11 | Sign out & back in | |
| 12 | Admin: update email | |
| 13 | Admin: send digest | |

**Overall result:** _______________  
**Issues found:** _______________
