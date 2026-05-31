# Brag Board — Learn Hub UAT Script
**URL:** https://brag.woodsandbryant.com/learn  
**Date:** _______________  
**Tester Name:** _______________  
**Device / Browser:** _______________

Mark each test **PASS ✅** or **FAIL ❌**. If it fails, jot a quick note on what happened.

---

## Test 1 — Learn Hub Navigation

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Log in and look at the top nav bar | A **📚 Learn** link is visible next to 🏆 Rewards | |
| 2 | Tap **📚 Learn** | Opens the Learn Hub browse page at /learn | |
| 3 | Page title shows **📚 Learn Hub** | Correct heading visible | |

**Notes:** _______________

---

## Test 2 — Browse Tasks (No Tasks Yet)

*Run this before any tasks have been added.*

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn with no categories or tasks created | Page shows an empty state message — "No tasks yet — check back soon!" | |

**Notes:** _______________

---

## Test 3 — Admin: Create a Category

*Must be logged in as admin.*

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On the Learn Hub page, tap **⚙️ Manage** in the top right | Opens /learn/admin | |
| 2 | In the **Categories** panel, enter a name (e.g. "Kitchen"), emoji (🍽️), and sort order (1) | Fields filled | |
| 3 | Tap **+ Add Category** | "Kitchen 🍽️" appears in the category list | |
| 4 | Add a second category (e.g. "Yard" 🌿, order 2) | Both categories now listed | |

**Notes:** _______________

---

## Test 4 — Admin: Create a Task (No Video)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On /learn/admin, in the **Add Task** section, enter title "Wipe down counters" | Title field filled | |
| 2 | Add a short description: "Clean all kitchen surfaces" | Description entered | |
| 3 | Select "Kitchen 🍽️" from the category dropdown | Category selected | |
| 4 | Leave YouTube URL blank | — | |
| 5 | Set bonus points to 30 first / 10 repeat, threshold 80% | Values entered | |
| 6 | Tap **+ Add Task** | Task "Wipe down counters" appears in the task table | |

**Notes:** _______________

---

## Test 5 — Admin: Create a Task with Video and Quiz

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | In **Add Task**, enter title "How to mow the lawn" | Title entered | |
| 2 | Select "Yard 🌿" category | Category selected | |
| 3 | Paste a real YouTube URL (e.g. https://youtu.be/dQw4w9WgXcQ) | URL entered | |
| 4 | Set bonus: 50 first / 10 repeat / threshold 80% | Values set | |
| 5 | Click **Question 1** to expand it | Quiz question fields appear | |
| 6 | Enter a question: "What should you do before mowing?" | Question text entered | |
| 7 | Fill in 4 choices (A–D) and select the correct answer | All 4 choices filled, correct selected | |
| 8 | Tap **+ Add Task** | Task appears in table with ▶ indicator in the Video column | |

**Notes:** _______________

---

## Test 6 — Browse Tasks with Categories

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn | Category filter buttons appear at the top: **All**, **Kitchen 🍽️**, **Yard 🌿** | |
| 2 | Task cards are shown for both categories under **All** | Both tasks visible | |
| 3 | Tap **Kitchen 🍽️** | Only "Wipe down counters" is shown | |
| 4 | Tap **Yard 🌿** | Only "How to mow the lawn" is shown | |
| 5 | Tap **All** | Both tasks are shown again | |
| 6 | The "How to mow the lawn" card shows **▶ Video** and **🎯 Quiz** badges | Both badges visible | |

**Notes:** _______________

---

## Test 7 — Task Detail Page (No Video)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Tap **Wipe down counters** | Opens task detail page | |
| 2 | Category label, title, and description are shown | All three visible | |
| 3 | No video player or progress bar is shown | Correct — no video for this task | |
| 4 | The brag text area is enabled and ready to type | No disabled state | |
| 5 | Bonus points panel on the right shows "+30 pts" | Correct value | |

**Notes:** _______________

---

## Test 8 — Task Detail Page (With Video)

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn and tap **How to mow the lawn** | Task detail page opens | |
| 2 | A YouTube video player is embedded on the page | Player visible and loads | |
| 3 | A watch progress bar shows **0%** | Bar at 0 | |
| 4 | The brag text area and submit button are **disabled** | Both greyed out / disabled | |
| 5 | Below the progress bar, text says "Watch 80% to unlock the quiz" | Message visible | |
| 6 | The right panel shows the bonus point breakdown (100% / 40% / 15% / repeat) | All four rows visible | |

**Notes:** _______________

---

## Test 9 — Watch Video and Unlock Quiz

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On the task detail page, press Play on the video | Video plays | |
| 2 | Watch for at least a few seconds | Progress bar begins to fill | |
| 3 | Continue watching until progress bar reaches **80%** or more | Bar shows 80%+ | |
| 4 | Page automatically reloads | — | |
| 5 | After reload, progress bar shows **✓ Video threshold reached — quiz unlocked!** | Message in green | |
| 6 | Quiz questions appear below the video | Questions visible | |
| 7 | Brag text area and **Log & Earn Points** button are now **enabled** | No longer disabled | |

**Notes:** _______________

---

## Test 10 — Complete Task: Pass Quiz and Earn Full Bonus

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On the unlocked task, answer all quiz questions correctly | All answers selected | |
| 2 | Type a brag in the text area (e.g. "I watched the lawn mowing video and mowed the backyard!") | Text entered | |
| 3 | Tap **Log & Earn Points** | Page redirects to main feed | |
| 4 | A green flash message appears: "🎉 Brag logged! You earned **+50 bonus pts** (3/3 on the quiz)" | Correct score and full bonus shown | |
| 5 | Your new brag appears at the top of the feed | Brag visible | |
| 6 | Your points balance increased by 50 (plus base category points) | Balance updated | |

**Notes:** _______________

---

## Test 11 — Complete Task: Partial Quiz Score

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go back to /learn, tap the task with quiz questions | Task detail opens (already watched) | |
| 2 | Answer only 1 out of 3 quiz questions correctly | Partial answers selected | |
| 3 | Type a brag and tap **Log & Earn Points** | Redirected to main feed | |
| 4 | Flash message shows partial bonus (e.g. "1/3 on the quiz", bonus ≈ 40% of max) | Reduced bonus shown | |

**Notes:** _______________

---

## Test 12 — Repeat Watch Earns Reduced Bonus

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Return to a task you've already completed | Task detail shows **♻️ Log again (repeat)** heading | |
| 2 | Your prior completion dates and bonuses are listed at the bottom | History visible | |
| 3 | The right panel shows **Repeat watch: 10 pts** | Correct repeat bonus shown | |
| 4 | Write a brag and tap **Log & Earn Points** | Redirected to feed | |
| 5 | Flash message shows **+10 bonus pts** (the repeat bonus) | Correct lower bonus | |

**Notes:** _______________

---

## Test 13 — Task Without Quiz Can Be Completed Without Watching

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Open **Wipe down counters** (no video, no quiz) | Task detail with brag form enabled immediately | |
| 2 | Type a brag and tap **Log & Earn Points** | Brag posts, bonus awarded | |
| 3 | Flash confirms brag logged with bonus | Bonus message shown | |

**Notes:** _______________

---

## Test 14 — Completion Badge on Browse Page

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn | Tasks you have already completed show a **✓ Done** green badge | |
| 2 | Tasks not yet completed show no badge | Correct — no badge | |

**Notes:** _______________

---

## Admin-Only Tests
*Skip these if you are not the admin.*

### Test 15 — Admin: Disable and Re-enable a Task

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn/admin, find a task in the table | Task listed | |
| 2 | Tap **⏸ Disable** | Task row becomes faded/dim | |
| 3 | Go to /learn | Disabled task no longer appears in the browse page | |
| 4 | Return to /learn/admin, tap **▶ Enable** on the task | Task row returns to normal | |
| 5 | Go to /learn | Task is visible again | |

**Notes:** _______________

---

### Test 16 — Admin: Delete a Task

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | Go to /learn/admin, tap **✕** on a task and confirm | Task disappears from the table | |
| 2 | Go to /learn | Deleted task no longer appears | |

**Notes:** _______________

---

### Test 17 — Admin: Edit Global Settings

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On /learn/admin, scroll to **Global Settings** | Settings form visible with current values | |
| 2 | Change **Watch threshold %** to 50 and tap **Save Settings** | "Learn Hub settings saved" confirmation | |
| 3 | Open a task with a video, watch past 50% | Quiz unlocks at 50% instead of 80% | |
| 4 | Reset the threshold back to 80 | Setting restored | |

**Notes:** _______________

---

### Test 18 — Admin: Add a Quiz Question to Existing Task

| Step | Action | Expected Result | Result |
|------|--------|-----------------|--------|
| 1 | On /learn/admin, find the task table | Tasks listed | |
| 2 | *(This requires adding a question via the Add Task form — re-create a task with a new question if needed)* | — | |
| 3 | Open the task detail page as a regular user | New question appears in the quiz | |

**Notes:** _______________

---

## Summary

| Test | Description | Result |
|------|-------------|--------|
| 1 | Learn Hub navigation | |
| 2 | Empty state (no tasks) | |
| 3 | Admin: create category | |
| 4 | Admin: create task (no video) | |
| 5 | Admin: create task with video and quiz | |
| 6 | Browse tasks with category filter | |
| 7 | Task detail — no video | |
| 8 | Task detail — with video, quiz locked | |
| 9 | Watch video and unlock quiz | |
| 10 | Complete — full quiz pass, full bonus | |
| 11 | Complete — partial quiz score, reduced bonus | |
| 12 | Repeat watch — reduced repeat bonus | |
| 13 | Task without video/quiz completes immediately | |
| 14 | Completion badge on browse page | |
| 15 | Admin: disable/enable task | |
| 16 | Admin: delete task | |
| 17 | Admin: edit global settings | |
| 18 | Admin: add quiz question | |

**Overall result:** _______________  
**Issues found:** _______________
