import streamlit as st
import sqlite3
import pandas as pd
import shutil
import base64
from pathlib import Path
from datetime import datetime
from car_data import CAR_LIST

# --- Database Setup ---
DB_PATH = "car_reviews.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS car_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spawn_name TEXT NOT NULL,
            original_tier TEXT NOT NULL,
            original_subclass TEXT NOT NULL,
            new_tier TEXT NOT NULL,
            reviewer_name TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_review(spawn_name, original_tier, original_subclass, new_tier, reviewer_name):
    conn = get_db()
    conn.execute(
        "INSERT INTO car_reviews (spawn_name, original_tier, original_subclass, new_tier, reviewer_name, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (spawn_name, original_tier, original_subclass, new_tier, reviewer_name, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_reviews():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM car_reviews ORDER BY id", conn)
    conn.close()
    return df


def get_reviewer_progress(reviewer_name, filtered_cars):
    conn = get_db()
    cursor = conn.execute(
        "SELECT DISTINCT spawn_name FROM car_reviews WHERE reviewer_name = ?",
        (reviewer_name,),
    )
    all_reviewed = {row[0] for row in cursor.fetchall()}
    conn.close()
    filtered_names = {c["spawn_name"] for c in filtered_cars}
    return all_reviewed & filtered_names


def get_completed_cars():
    """Cars are completed (removed from review) when:
    - 3 people voted the same tier, OR
    - 5 people have voted regardless of spread
    """
    conn = get_db()
    cursor = conn.execute("""
        SELECT spawn_name, new_tier, COUNT(DISTINCT reviewer_name) as cnt
        FROM car_reviews
        GROUP BY spawn_name, new_tier
    """)
    # Check for 3 agreeing on same tier
    consensus_done = set()
    for row in cursor.fetchall():
        if row[2] >= 3:
            consensus_done.add(row[0])

    # Check for 5 total unique voters
    cursor2 = conn.execute("""
        SELECT spawn_name, COUNT(DISTINCT reviewer_name) as cnt
        FROM car_reviews
        GROUP BY spawn_name
        HAVING cnt >= 5
    """)
    volume_done = {row[0] for row in cursor2.fetchall()}

    conn.close()
    return consensus_done | volume_done


# --- Page Config ---
st.set_page_config(page_title="Car Re-Tier", page_icon="🏎️", layout="centered")

# --- Mobile-First CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0 !important; max-width: 600px !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu, footer { display: none; }
    .stApp { background-color: #0e1117; }

    .car-hero {
        background: linear-gradient(135deg, #1a1d24 0%, #13161c 100%);
        border: 1px solid #2d3139;
        border-radius: 16px;
        padding: 1.25rem 1rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .car-counter { color: #6b7280; font-size: 0.8rem; letter-spacing: 0.05em; }
    .car-name {
        color: #e6e9ef;
        font-family: 'Courier New', monospace;
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0.4rem 0;
        word-break: break-all;
    }
    .car-info {
        color: #9ca3af;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }
    .car-info span {
        margin: 0 0.3rem;
    }
    .tb {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.8rem;
        vertical-align: middle;
    }
    .tb-s { background: #dc2626; color: #fff; }
    .tb-a { background: #f59e0b; color: #000; }
    .tb-b { background: #3b82f6; color: #fff; }
    .tb-c { background: #10b981; color: #fff; }
    .tb-special { background: #0ea5e9; color: #fff; }
    .tb-misc { background: #64748b; color: #fff; }

    .prog {
        background: #1e2028;
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.75rem;
        border: 1px solid #2d3139;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .prog-text { color: #9ca3af; font-size: 0.75rem; white-space: nowrap; }
    .prog-track { flex: 1; background: #2d3139; border-radius: 4px; height: 6px; }
    .prog-fill { background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 4px; height: 6px; }

    div.stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
        width: 100% !important;
        min-height: 52px !important;
        -webkit-tap-highlight-color: transparent;
    }
    div.stButton > button:active { transform: scale(0.97); }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; justify-content: center; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1d24; border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem; color: #9ca3af; font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] { background-color: #2d3139; color: #e6e9ef; }

    .login-card {
        background: linear-gradient(135deg, #1a1d24 0%, #13161c 100%);
        border: 1px solid #2d3139; border-radius: 16px;
        padding: 2rem 1.5rem; text-align: center; margin-top: 2rem;
    }
    .login-card h2 { color: #e6e9ef; font-size: 1.2rem; margin-bottom: 0.5rem; }
    .login-card p { color: #6b7280; font-size: 0.85rem; }
    .top-logo {
        position: fixed;
        top: 10px;
        left: 12px;
        z-index: 9999;
        width: 36px;
        height: auto;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# --- Logo ---
logo_path = Path(__file__).parent / "logo.png"
if logo_path.exists():
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    st.markdown(f'<img src="data:image/png;base64,{logo_b64}" class="top-logo">', unsafe_allow_html=True)

# --- Session State ---
if "car_index" not in st.session_state:
    st.session_state.car_index = 0
if "reviewer" not in st.session_state:
    st.session_state.reviewer = ""
if "tier_filter" not in st.session_state:
    st.session_state.tier_filter = "All"
if "results_unlocked" not in st.session_state:
    st.session_state.results_unlocked = False

TIER_COLORS = {
    "S": "tb-s", "A": "tb-a", "B": "tb-b",
    "C": "tb-c", "Special": "tb-special", "Misc": "tb-misc",
}
ASSIGNABLE_TIERS = ["S", "A", "B", "C", "Special"]
FILTER_TIERS = ["All", "S", "A", "B", "C", "Special", "Misc"]

# --- Tabs ---
tab_review, tab_results = st.tabs(["Review", "Results"])

# ====== REVIEW TAB ======
with tab_review:
    if not st.session_state.reviewer:
        st.markdown("""
        <div class="login-card">
            <h2>Car Re-Tiering Tool</h2>
            <p>Enter your name to start reviewing</p>
        </div>
        """, unsafe_allow_html=True)
        name = st.text_input("Your name", label_visibility="collapsed", placeholder="Your name...")
        if st.button("Start", use_container_width=True, type="primary"):
            if name.strip():
                st.session_state.reviewer = name.strip()
                st.rerun()
    else:
        reviewer_name = st.session_state.reviewer

        # Tier filter
        selected_filter = st.selectbox(
            "Filter by tier",
            FILTER_TIERS,
            index=FILTER_TIERS.index(st.session_state.tier_filter),
            label_visibility="collapsed",
        )
        if selected_filter != st.session_state.tier_filter:
            st.session_state.tier_filter = selected_filter
            st.session_state.car_index = 0
            st.rerun()

        # Filtered car list (exclude completed cars)
        completed = get_completed_cars()
        if st.session_state.tier_filter == "All":
            filtered_cars = [c for c in CAR_LIST if c["spawn_name"] not in completed]
        else:
            filtered_cars = [c for c in CAR_LIST if c["tier"] == st.session_state.tier_filter and c["spawn_name"] not in completed]

        total = len(filtered_cars)

        if total == 0:
            st.info("All cars in this tier are done!")
        else:
            reviewed = get_reviewer_progress(reviewer_name, filtered_cars)
            done = len(reviewed)

            # Progress
            pct = (done / total) * 100
            st.markdown(f"""
            <div class="prog">
                <span class="prog-text">{done}/{total}</span>
                <div class="prog-track"><div class="prog-fill" style="width:{pct:.1f}%"></div></div>
                <span class="prog-text">{reviewer_name}</span>
            </div>
            """, unsafe_allow_html=True)

            idx = max(0, min(st.session_state.car_index, total - 1))
            st.session_state.car_index = idx

            car = filtered_cars[idx]
            spawn = car["spawn_name"]
            tier = car["tier"]
            subclass = car["subclass"]
            tier_class = TIER_COLORS.get(tier, "tb-misc")

            # Car card — spawn name + tier & category only
            st.markdown(f"""
            <div class="car-hero">
                <div class="car-counter">#{idx + 1} of {total}</div>
                <div class="car-name">{spawn}</div>
                <div class="car-info">
                    <span class="tb {tier_class}">{tier}</span>
                    <span>{subclass}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Tier buttons — S A B C in one row, Special below
            st.markdown("<div style='text-align:center;color:#6b7280;font-size:0.8rem;margin-bottom:0.4rem;'>Assign tier:</div>", unsafe_allow_html=True)

            row1 = st.columns(4)
            for i, t in enumerate(["S", "A", "B", "C"]):
                with row1[i]:
                    if st.button(t, key=f"t_{t}_{idx}", use_container_width=True):
                        save_review(spawn, tier, subclass, t, reviewer_name)
                        if idx < total - 1:
                            st.session_state.car_index = idx + 1
                        st.rerun()

            if st.button("Special", key=f"t_Special_{idx}", use_container_width=True):
                save_review(spawn, tier, subclass, "Special", reviewer_name)
                if idx < total - 1:
                    st.session_state.car_index = idx + 1
                st.rerun()

            # Navigation
            st.markdown("")
            nav = st.columns(3)
            with nav[0]:
                if st.button("Prev", disabled=(idx == 0), key="nav_prev", use_container_width=True):
                    st.session_state.car_index = idx - 1
                    st.rerun()
            with nav[1]:
                if st.button("Skip to next", key="nav_skip", use_container_width=True):
                    found = False
                    for j in range(idx + 1, total):
                        if filtered_cars[j]["spawn_name"] not in reviewed:
                            st.session_state.car_index = j
                            found = True
                            break
                    if not found:
                        for j in range(0, idx):
                            if filtered_cars[j]["spawn_name"] not in reviewed:
                                st.session_state.car_index = j
                                found = True
                                break
                    if not found:
                        st.toast("All done!")
                    st.rerun()
            with nav[2]:
                if st.button("Next", disabled=(idx >= total - 1), key="nav_next", use_container_width=True):
                    st.session_state.car_index = idx + 1
                    st.rerun()

            # Jump to car
            with st.expander("Jump to car"):
                jcol1, jcol2 = st.columns([2, 1])
                with jcol1:
                    jump = st.number_input("Car #", min_value=1, max_value=total, value=idx + 1, step=1, label_visibility="collapsed")
                with jcol2:
                    if st.button("Go", use_container_width=True):
                        st.session_state.car_index = jump - 1
                        st.rerun()


# ====== RESULTS TAB (password protected) ======
with tab_results:
    if not st.session_state.results_unlocked:
        st.markdown("")
        pw = st.text_input("Enter password to view results", type="password", placeholder="Password...")
        if st.button("Unlock", use_container_width=True, type="primary"):
            if pw == "Baldie123":
                st.session_state.results_unlocked = True
                st.rerun()
            else:
                st.error("Wrong password.")
    else:
        df = get_all_reviews()

        if df.empty:
            st.info("No reviews yet.")
        else:
            completed = get_completed_cars()
            total_cars = len(CAR_LIST)
            done_count = len(completed)
            done_pct = (done_count / total_cars) * 100 if total_cars > 0 else 0

            # Overall progress bar
            st.markdown(f"""
            <div class="prog" style="margin-bottom:1rem;">
                <span class="prog-text">{done_count}/{total_cars} completed</span>
                <div class="prog-track"><div class="prog-fill" style="width:{done_pct:.1f}%"></div></div>
                <span class="prog-text">{done_pct:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Votes", len(df))
            c2.metric("Cars Voted On", df["spawn_name"].nunique())
            c3.metric("Reviewers", df["reviewer_name"].nunique())

            st.markdown("### Consensus")
            consensus_data = []
            for spawn in df["spawn_name"].unique():
                car_reviews = df[df["spawn_name"] == spawn]
                orig_tier = car_reviews["original_tier"].iloc[0]
                tier_votes = car_reviews["new_tier"].value_counts().to_dict()
                majority = max(tier_votes, key=tier_votes.get)
                n_voters = len(car_reviews)
                agree = "Yes" if len(tier_votes) == 1 and n_voters > 1 else ("Pending" if n_voters == 1 else "No")
                reviews_str = ", ".join([f"{r}:{t}" for r, t in car_reviews[["reviewer_name", "new_tier"]].values.tolist()])
                consensus_data.append({
                    "Car": spawn,
                    "Was": orig_tier,
                    "Vote": majority,
                    "Agree": agree,
                    "Votes": reviews_str,
                })

            consensus_df = pd.DataFrame(consensus_data)
            st.dataframe(consensus_df, use_container_width=True, hide_index=True)

            # Build clean export CSV
            export_data = []
            for spawn in df["spawn_name"].unique():
                car_reviews = df[df["spawn_name"] == spawn]
                orig_tier = car_reviews["original_tier"].iloc[0]
                orig_subclass = car_reviews["original_subclass"].iloc[0]
                tier_votes = car_reviews["new_tier"].value_counts().to_dict()
                majority = max(tier_votes, key=tier_votes.get)
                n_voters = len(car_reviews)
                unanimous = "Yes" if len(tier_votes) == 1 and n_voters > 1 else ("Pending" if n_voters == 1 else "No")
                changed = "Yes" if majority != orig_tier else "No"

                row = {
                    "Spawn Name": spawn,
                    "Original Tier": orig_tier,
                    "Subclass": orig_subclass,
                    "New Tier": majority,
                    "Changed": changed,
                    "Agreement": unanimous,
                    "Total Votes": n_voters,
                }
                # Add individual reviewer columns
                for _, r in car_reviews.iterrows():
                    row[r["reviewer_name"]] = r["new_tier"]
                export_data.append(row)

            export_df = pd.DataFrame(export_data)

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button("Export Results CSV", export_df.to_csv(index=False), "retiering_results.csv", "text/csv", use_container_width=True)
            with dl2:
                st.download_button("Raw Votes CSV", df.to_csv(index=False), "raw_votes.csv", "text/csv", use_container_width=True)

            with st.expander("Admin"):
                st.warning("Permanently delete reviews.")
                del_reviewer = st.text_input("Reviewer name:")
                del_spawn = st.text_input("Spawn name (blank = all for reviewer):")
                if st.button("Delete", type="primary"):
                    if del_reviewer:
                        conn = get_db()
                        if del_spawn:
                            conn.execute("DELETE FROM car_reviews WHERE reviewer_name = ? AND spawn_name = ?", (del_reviewer, del_spawn))
                        else:
                            conn.execute("DELETE FROM car_reviews WHERE reviewer_name = ?", (del_reviewer,))
                        conn.commit()
                        conn.close()
                        st.success("Deleted.")
                        st.rerun()

        # Backup & Restore (always visible when unlocked)
        st.markdown("---")
        st.markdown("### Backup & Restore")

        st.download_button(
            "Download Backup CSV",
            get_all_reviews().to_csv(index=False) if not get_all_reviews().empty else "",
            "backup_votes.csv",
            "text/csv",
            use_container_width=True,
            disabled=get_all_reviews().empty,
        )

        uploaded = st.file_uploader("Upload backup CSV to restore", type=["csv"], label_visibility="collapsed")
        if uploaded is not None:
            if st.button("Restore from CSV", use_container_width=True, type="primary"):
                try:
                    imported_df = pd.read_csv(uploaded)
                    required_cols = {"spawn_name", "original_tier", "original_subclass", "new_tier", "reviewer_name", "timestamp"}
                    if not required_cols.issubset(set(imported_df.columns)):
                        st.error(f"CSV missing columns: {required_cols - set(imported_df.columns)}")
                    else:
                        conn = get_db()
                        imported_df[list(required_cols)].to_sql("car_reviews", conn, if_exists="append", index=False)
                        conn.close()
                        st.success(f"Restored {len(imported_df)} votes.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")
