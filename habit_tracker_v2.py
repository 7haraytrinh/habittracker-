"""
📅 Habit Tracker v2 — with the improvement note system!

HOW TO RUN:
  pip install streamlit pandas
  streamlit run habit_tracker_v2.py

WHAT'S NEW vs v1:
  - After checking off a task, you can write an improvement note
    (e.g. "còn góc dưới tủ chưa lau, lần sau nhớ lau")
  - The next time that task appears, your note shows up IN THE GRID
    as a reminder, with a "Done ✓" button to resolve it
  - Each task keeps a timeline of notes: open vs resolved
  - Weekly grid + regularity report kept from v1
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import date, timedelta

DATA_FILE = "habits.json"

# ─────────────────────────────────────────────
# 1. SAVE / LOAD — now with a "notes" list
# ─────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:   # utf-8 = Vietnamese-safe!
            data = json.load(f)
        data.setdefault("notes", [])   # upgrade old v1 files gracefully
        return data
    return {"tasks": [], "completions": [], "notes": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps Vietnamese readable in the file
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────
# 2. HELPERS
# ─────────────────────────────────────────────
def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_label(monday: date) -> str:
    return f"{monday.strftime('%b %d')} – {(monday + timedelta(days=6)).strftime('%b %d')}"

def open_note_for(task_name, notes):
    """Return the most recent UNRESOLVED note for a task, or None."""
    open_notes = [n for n in notes if n["task"] == task_name and not n["resolved"]]
    if open_notes:
        return max(open_notes, key=lambda n: n["date"])   # newest first
    return None

# ─────────────────────────────────────────────
# 3. SETUP
# ─────────────────────────────────────────────
st.set_page_config(page_title="Habit Tracker v2", page_icon="📅", layout="wide")
st.title("📅 Habit Tracker")
st.caption("Check off tasks, note what to improve, and see the reminder next time.")

if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# ─────────────────────────────────────────────
# 4. SIDEBAR — manage tasks
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("➕ Add a task")
    new_task = st.text_input("Task name", placeholder="e.g. Lau nhà")
    target = st.slider("Goal: days per week", 1, 7, 3)
    if st.button("Add task", type="primary", use_container_width=True):
        existing = [t["name"] for t in data["tasks"]]
        if new_task and new_task not in existing:
            data["tasks"].append({"name": new_task, "target": target})
            save_data(data)
            st.rerun()
        elif new_task in existing:
            st.warning("That task already exists!")
        else:
            st.warning("Give your task a name first.")

    if data["tasks"]:
        st.divider()
        st.header("🗑️ Remove a task")
        to_delete = st.selectbox("Pick one", [t["name"] for t in data["tasks"]])
        if st.button("Delete", use_container_width=True):
            data["tasks"] = [t for t in data["tasks"] if t["name"] != to_delete]
            data["completions"] = [c for c in data["completions"] if c["task"] != to_delete]
            data["notes"] = [n for n in data["notes"] if n["task"] != to_delete]
            save_data(data)
            st.rerun()

if not data["tasks"]:
    st.info("👈 Add your first task in the sidebar to get started!")
    st.stop()

# ─────────────────────────────────────────────
# 5. WEEK NAVIGATION
# ─────────────────────────────────────────────
if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("⬅️ Previous week"):
        st.session_state.week_offset -= 1
        st.rerun()
with nav3:
    if st.button("Next week ➡️", disabled=st.session_state.week_offset >= 0):
        st.session_state.week_offset += 1
        st.rerun()

monday = week_start(date.today()) + timedelta(weeks=st.session_state.week_offset)
with nav2:
    label = week_label(monday)
    if st.session_state.week_offset == 0:
        label += "  (this week)"
    st.markdown(f"<h4 style='text-align:center'>{label}</h4>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 6. THE GRID — checkboxes + in-grid note reminders
# ─────────────────────────────────────────────
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
week_dates = [monday + timedelta(days=i) for i in range(7)]
done_set = {(c["task"], c["date"]) for c in data["completions"]}
today_str = date.today().isoformat()

header_cols = st.columns([3] + [1] * 7 + [2])
header_cols[0].markdown("**Task**")
for i, day in enumerate(day_names):
    header_cols[i + 1].markdown(f"**{day}**<br>{week_dates[i].day}", unsafe_allow_html=True)
header_cols[8].markdown("**This week**")

for task in data["tasks"]:
    name = task["name"]
    cols = st.columns([3] + [1] * 7 + [2])
    cols[0].write(name)

    week_count = 0
    checked_today = False

    for i, d in enumerate(week_dates):
        d_str = d.isoformat()
        checked = (name, d_str) in done_set
        new_val = cols[i + 1].checkbox(
            label=f"{name} {d_str}",
            value=checked,
            key=f"chk_{name}_{d_str}",
            disabled=(d > date.today()),
            label_visibility="collapsed",
        )
        if new_val and not checked:
            data["completions"].append({"task": name, "date": d_str})
            save_data(data)
        elif not new_val and checked:
            data["completions"] = [
                c for c in data["completions"]
                if not (c["task"] == name and c["date"] == d_str)
            ]
            save_data(data)
        if new_val:
            week_count += 1
        if new_val and d_str == today_str:
            checked_today = True

    cols[8].progress(min(week_count / task["target"], 1.0),
                     text=f"{week_count}/{task['target']}")

    # ── THE REMINDER (in the grid, as you chose!) ──
    reminder = open_note_for(name, data["notes"])
    if reminder:
        r1, r2 = st.columns([6, 1])
        r1.warning(f"🔔 Last time ({reminder['date']}): {reminder['note']}")
        if r2.button("Done ✓", key=f"resolve_{name}_{reminder['date']}"):
            reminder["resolved"] = True          # dicts are shared, so this
            reminder["resolved_date"] = today_str  # edits data['notes'] directly
            save_data(data)
            st.rerun()

    # ── NEW NOTE input — appears only when checked off today ──
    if checked_today:
        # Only offer a new note if there's no open one already
        has_note_today = any(n["task"] == name and n["date"] == today_str
                             for n in data["notes"])
        if not has_note_today:
            n1, n2 = st.columns([6, 1])
            note_text = n1.text_input(
                "Improve next time (optional)",
                key=f"note_{name}_{today_str}",
                placeholder="e.g. còn góc dưới tủ chưa lau, lần sau nhớ lau",
                label_visibility="collapsed",
            )
            if n2.button("Save note", key=f"save_{name}_{today_str}"):
                if note_text.strip():
                    data["notes"].append({
                        "task": name,
                        "date": today_str,
                        "note": note_text.strip(),
                        "resolved": False,
                        "resolved_date": None,
                    })
                    save_data(data)
                    st.rerun()

    st.divider()

# ─────────────────────────────────────────────
# 7. IMPROVEMENT HISTORY — per-task note timeline
# ─────────────────────────────────────────────
st.subheader("📝 Improvement history")

sel_task = st.selectbox("Task", [t["name"] for t in data["tasks"]])
task_notes = sorted(
    [n for n in data["notes"] if n["task"] == sel_task],
    key=lambda n: n["date"], reverse=True,          # newest first
)

if task_notes:
    resolved_count = sum(1 for n in task_notes if n["resolved"])
    total = len(task_notes)
    rate = resolved_count / total
    c1, c2 = st.columns([1, 3])
    c1.metric("Notes resolved", f"{resolved_count} / {total}")
    c2.progress(rate, text=f"Follow-through: {rate:.0%}")

    for n in task_notes:
        if n["resolved"]:
            st.markdown(f"✅ **{n['date']}** — ~~{n['note']}~~ "
                        f"*(resolved {n['resolved_date']})*")
        else:
            st.markdown(f"🟠 **{n['date']}** — {n['note']} *(open)*")
else:
    st.info("No notes yet for this task. Check it off today and add one!")

# ─────────────────────────────────────────────
# 8. REGULARITY REPORT — same logic as v1
# ─────────────────────────────────────────────
st.divider()
st.subheader("📊 Regularity report (last 4 weeks)")

report_rows = []
this_monday = week_start(date.today())

for task in data["tasks"]:
    weekly_counts = []
    for w in range(4):
        wk_monday = this_monday - timedelta(weeks=w)
        wk_dates = {(wk_monday + timedelta(days=i)).isoformat() for i in range(7)}
        count = sum(1 for c in data["completions"]
                    if c["task"] == task["name"] and c["date"] in wk_dates)
        weekly_counts.append(count)

    goal = task["target"]
    weeks_hit = sum(1 for c in weekly_counts if c >= goal)
    avg = sum(weekly_counts) / 4

    if weeks_hit >= 3:
        flag = "🟢 Regular"
    elif weeks_hit >= 2 or avg >= goal * 0.6:
        flag = "🟡 Getting there"
    else:
        flag = "🔴 Irregular"

    # Bonus: count open notes so nagging reminders are visible here too
    open_notes = sum(1 for n in data["notes"]
                     if n["task"] == task["name"] and not n["resolved"])

    report_rows.append({
        "Task": task["name"],
        "Goal / week": goal,
        "This week": weekly_counts[0],
        "Weeks goal hit": f"{weeks_hit}/4",
        "Open notes": open_notes,
        "Regularity": flag,
    })

st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# YOUR HOMEWORK:
#   1. Easy:   change the reminder from st.warning (yellow) to st.info (blue)
#   2. Medium: let the user EDIT an open note instead of only resolving it
#   3. Hard:   auto-resolve — when saving a NEW note for a task, ask whether
#              the previous open note was handled
# ─────────────────────────────────────────────
