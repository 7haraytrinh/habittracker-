"""
📅 Habit Tracker v3 — mobile-friendly edition

WHAT CHANGED vs v2 (and why):
  PROBLEM: st.columns WRAP on narrow screens, so the checkbox grid
  fell apart on mobile — checkboxes no longer lined up with dates.

  FIX 1: A "Today" section at the top — a simple vertical list
         (checkbox + reminder + note per task). Vertical layouts
         are naturally mobile-proof. This is what you'll use on
         your phone 90% of the time.

  FIX 2: The week grid is now st.data_editor — a real table widget
         with checkbox cells. Real tables keep headers and cells
         aligned, and scroll horizontally as one unit on mobile.

RUN:  streamlit run habit_tracker_v3.py
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import date, timedelta

DATA_FILE = "habits.json"

# ─────────────────────────────────────────────
# 1. SAVE / LOAD (unchanged from v2)
# ─────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("notes", [])
        return data
    return {"tasks": [], "completions": [], "notes": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def open_note_for(task_name, notes):
    open_notes = [n for n in notes if n["task"] == task_name and not n["resolved"]]
    return max(open_notes, key=lambda n: n["date"]) if open_notes else None

# ─────────────────────────────────────────────
# 2. SETUP  — layout="centered" reads better on phones
# ─────────────────────────────────────────────
st.set_page_config(page_title="Habit Tracker", page_icon="📅", layout="centered")
st.title("📅 Habit Tracker")

if "data" not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# ─────────────────────────────────────────────
# 3. SIDEBAR — manage tasks (unchanged)
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
    st.info("👈 Add your first task in the sidebar (tap » on mobile).")
    st.stop()

today_str = date.today().isoformat()
done_set = {(c["task"], c["date"]) for c in data["completions"]}

def toggle_completion(name, d_str, new_val):
    """Add or remove one completion record, then save. One function,
    used by BOTH the Today view and the week grid — no duplicated logic."""
    currently = (name, d_str) in done_set
    if new_val and not currently:
        data["completions"].append({"task": name, "date": d_str})
        save_data(data)
    elif not new_val and currently:
        data["completions"][:] = [
            c for c in data["completions"]
            if not (c["task"] == name and c["date"] == d_str)
        ]
        save_data(data)

# ─────────────────────────────────────────────
# 4. TODAY VIEW — mobile-first, simple vertical list
# ─────────────────────────────────────────────
st.subheader(f"✅ Today · {date.today().strftime('%a %b %d')}")

for task in data["tasks"]:
    name = task["name"]
    done_today = (name, today_str) in done_set

    checked = st.checkbox(name, value=done_today, key=f"today_{name}")
    if checked != done_today:
        toggle_completion(name, today_str, checked)
        st.rerun()

    # Reminder (the improvement note system, same as v2)
    reminder = open_note_for(name, data["notes"])
    if reminder:
        st.warning(f"🔔 Last time ({reminder['date']}): {reminder['note']}")
        if st.button("Done ✓", key=f"resolve_{name}_{reminder['date']}"):
            reminder["resolved"] = True
            reminder["resolved_date"] = today_str
            save_data(data)
            st.rerun()

    # Offer a new note only when checked today and none written yet today
    if checked:
        has_note_today = any(n["task"] == name and n["date"] == today_str
                             for n in data["notes"])
        if not has_note_today:
            with st.expander("📝 Improve next time (optional)"):
                note_text = st.text_input(
                    "Note", key=f"note_{name}_{today_str}",
                    placeholder="e.g. còn góc dưới tủ chưa lau",
                    label_visibility="collapsed",
                )
                if st.button("Save note", key=f"save_{name}_{today_str}"):
                    if note_text.strip():
                        data["notes"].append({
                            "task": name, "date": today_str,
                            "note": note_text.strip(),
                            "resolved": False, "resolved_date": None,
                        })
                        save_data(data)
                        st.rerun()

st.divider()

# ─────────────────────────────────────────────
# 5. WEEK GRID — st.data_editor keeps everything aligned
# ─────────────────────────────────────────────
st.subheader("📆 This week")

if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0

nav1, nav2, nav3 = st.columns([1, 2, 1])
if nav1.button("⬅️", help="Previous week"):
    st.session_state.week_offset -= 1
    st.rerun()
if nav3.button("➡️", help="Next week",
               disabled=st.session_state.week_offset >= 0):
    st.session_state.week_offset += 1
    st.rerun()

monday = week_start(date.today()) + timedelta(weeks=st.session_state.week_offset)
week_dates = [monday + timedelta(days=i) for i in range(7)]
nav2.markdown(
    f"<p style='text-align:center; margin-top:6px;'>"
    f"{monday.strftime('%b %d')} – {week_dates[-1].strftime('%b %d')}"
    f"{' (this week)' if st.session_state.week_offset == 0 else ''}</p>",
    unsafe_allow_html=True,
)

# Build a DataFrame: one row per task, one column per day, True/False cells
col_labels = [d.strftime("%a %d") for d in week_dates]        # "Mon 07", ...
grid_rows = {}
for task in data["tasks"]:
    grid_rows[task["name"]] = [
        (task["name"], d.isoformat()) in done_set for d in week_dates
    ]
grid_df = pd.DataFrame.from_dict(grid_rows, orient="index", columns=col_labels)

# Future days can't be edited
future_cols = [col_labels[i] for i, d in enumerate(week_dates) if d > date.today()]

edited_df = st.data_editor(
    grid_df,
    column_config={
        label: st.column_config.CheckboxColumn(label, width="small")
        for label in col_labels
    },
    disabled=future_cols,          # lock future columns
    use_container_width=True,
    key=f"grid_{monday.isoformat()}",   # separate state per week
)

# DIFF the edited grid vs the original: whatever changed, save it
changed = False
for name in grid_df.index:                       # each task
    for i, label in enumerate(col_labels):       # each day
        before = bool(grid_df.loc[name, label])
        after = bool(edited_df.loc[name, label])
        if before != after:
            toggle_completion(name, week_dates[i].isoformat(), after)
            changed = True
if changed:
    st.rerun()

# Weekly progress per task, as compact text (mobile-safe, no columns)
for task in data["tasks"]:
    count = sum(
        1 for d in week_dates
        if (task["name"], d.isoformat()) in done_set
    )
    st.progress(min(count / task["target"], 1.0),
                text=f"{task['name']}: {count}/{task['target']}")

st.divider()

# ─────────────────────────────────────────────
# 6. IMPROVEMENT HISTORY (unchanged from v2)
# ─────────────────────────────────────────────
st.subheader("📝 Improvement history")
sel_task = st.selectbox("Task", [t["name"] for t in data["tasks"]])
task_notes = sorted(
    [n for n in data["notes"] if n["task"] == sel_task],
    key=lambda n: n["date"], reverse=True,
)
if task_notes:
    resolved_count = sum(1 for n in task_notes if n["resolved"])
    rate = resolved_count / len(task_notes)
    st.progress(rate, text=f"Follow-through: {resolved_count}/{len(task_notes)} notes resolved")
    for n in task_notes:
        if n["resolved"]:
            st.markdown(f"✅ **{n['date']}** — ~~{n['note']}~~ *(resolved {n['resolved_date']})*")
        else:
            st.markdown(f"🟠 **{n['date']}** — {n['note']} *(open)*")
else:
    st.info("No notes yet for this task.")

st.divider()

# ─────────────────────────────────────────────
# 7. REGULARITY REPORT (unchanged from v2)
# ─────────────────────────────────────────────
st.subheader("📊 Regularity (last 4 weeks)")
report_rows = []
this_monday = week_start(date.today())
for task in data["tasks"]:
    weekly_counts = []
    for w in range(4):
        wk_monday = this_monday - timedelta(weeks=w)
        wk_dates = {(wk_monday + timedelta(days=i)).isoformat() for i in range(7)}
        weekly_counts.append(sum(
            1 for c in data["completions"]
            if c["task"] == task["name"] and c["date"] in wk_dates
        ))
    goal = task["target"]
    weeks_hit = sum(1 for c in weekly_counts if c >= goal)
    avg = sum(weekly_counts) / 4
    if weeks_hit >= 3:
        flag = "🟢 Regular"
    elif weeks_hit >= 2 or avg >= goal * 0.6:
        flag = "🟡 Getting there"
    else:
        flag = "🔴 Irregular"
    open_notes = sum(1 for n in data["notes"]
                     if n["task"] == task["name"] and not n["resolved"])
    report_rows.append({
        "Task": task["name"], "Goal": goal, "This wk": weekly_counts[0],
        "Hit": f"{weeks_hit}/4", "Open notes": open_notes, "Flag": flag,
    })
st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# HOMEWORK:
#   1. Easy:   reorder the page — try putting Improvement history above
#              the week grid. Which order feels better on your phone?
#   2. Medium: in the Today view, show a small 🔥 streak counter next to
#              each task name (consecutive days ending today)
#   3. Hard:   read about st.tabs and put Today / Week / History / Report
#              into four tabs — a very mobile-friendly pattern
# ─────────────────────────────────────────────
