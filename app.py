import streamlit as st
import sqlite3
import pandas as pd
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
    .car-meta {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-top: 0.4rem;
    }
    .tb {
        display: inline-block;
        padding: 0.2rem 0.9rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .tb-s { background: #dc2626; color: #fff; }
    .tb-a { background: #f59e0b; color: #000; }
    .tb-b { background: #3b82f6; color: #fff; }
    .tb-c { background: #10b981; color: #fff; }
    .tb-special { background: #0ea5e9; color: #fff; }
    .tb-misc { background: #64748b; color: #fff; }
    .sub-badge {
        color: #6b7280;
        font-size: 0.75rem;
        border: 1px solid #374151;
        border-radius: 4px;
        padding: 0.15rem 0.5rem;
    }
    .reviewed-tag {
        background: #065f46;
        color: #6ee7b7;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
    }
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
</style>
""", unsafe_allow_html=True)

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

# Available tiers to assign
ASSIGNABLE_TIERS = ["S", "A", "B", "C", "Special"]

# Tiers available for filtering
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

        # Tier filter selector
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

        # Build filtered car list
        if st.session_state.tier_filter == "All":
            filtered_cars = CAR_LIST
        else:
            filtered_cars = [c for c in CAR_LIST if c["tier"] == st.session_state.tier_filter]

        total = len(filtered_cars)

        if total == 0:
            st.info("No cars in this tier.")
        else:
            reviewed = get_reviewer_progress(reviewer_name, filtered_cars)
            done = len(reviewed)

            # Progress bar
            pct = (done / total) * 100
            st.markdown(f"""
            <div class="prog">
                <span class="prog-text">{done}/{total}</span>
                <div class="prog-track"><div class="prog-fill" style="width:{pct:.1f}%"></div></div>
                <span class="prog-text">{reviewer_name}</span>
            </div>
            """, unsafe_allow_html=True)

            idx = st.session_state.car_index
            idx = max(0, min(idx, total - 1))
            st.session_state.car_index = idx

            car = filtered_cars[idx]
            spawn = car["spawn_name"]
            tier = car["tier"]
            subclass = car["subclass"]
            already_reviewed = spawn in reviewed
            tier_class = TIER_COLORS.get(tier, "tb-misc")

            reviewed_html = '<span class="reviewed-tag">DONE</span>' if already_reviewed else ""

            # Car card — name, current tier, classification
            st.markdown(f"""
            <div class="car-hero">
                <div class="car-counter">#{idx + 1} of {total}</div>
                <div class="car-name">{spawn}</div>
                <div class="car-meta">
                    <span class="tb {tier_class}">{tier}</span>
                    <span class="sub-badge">{subclass}</span>
                    {reviewed_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Tier buttons — S, A, B, C in top row, Special + Keep in bottom row
            st.markdown("<div style='text-align:center;color:#6b7280;font-size:0.8rem;margin-bottom:0.4rem;'>Assign tier:</div>", unsafe_allow_html=True)

            row1 = st.columns(4)
            for i, t in enumerate(["S", "A", "B", "C"]):
                with row1[i]:
                    if st.button(t, key=f"t_{t}_{idx}", use_container_width=True):
                        save_review(spawn, tier, subclass, t, reviewer_name)
                        if idx < total - 1:
                            st.session_state.car_index = idx + 1
                        st.rerun()

            row2 = st.columns(2)
            with row2[0]:
                if st.button("Special", key=f"t_Special_{idx}", use_container_width=True):
                    save_review(spawn, tier, subclass, "Special", reviewer_name)
                    if idx < total - 1:
                        st.session_state.car_index = idx + 1
                    st.rerun()
            with row2[1]:
                if st.button(f"Keep {tier}", key=f"keep_{idx}", use_container_width=True):
                    save_review(spawn, tier, subclass, tier, reviewer_name)
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

        # Switch user (always visible)
        st.markdown("")
        if st.button("Switch user", key="logout"):
            st.session_state.reviewer = ""
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
            c1, c2, c3 = st.columns(3)
            c1.metric("Reviews", len(df))
            c2.metric("Cars", df["spawn_name"].nunique())
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

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button("All Reviews CSV", df.to_csv(index=False), "reviews.csv", "text/csv", use_container_width=True)
            with dl2:
                st.download_button("Consensus CSV", consensus_df.to_csv(index=False), "consensus.csv", "text/csv", use_container_width=True)

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
