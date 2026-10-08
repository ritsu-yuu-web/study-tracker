import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

st.set_page_config(page_title="学習時間トラッカー", layout="wide")

# ----------------------
# SQLite3 データベース設定
# ----------------------
DB_PATH = "study_tracker.db"

def init_db():
    """データベースと学習記録テーブルを作成する（初回のみ）。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS study_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_date TEXT NOT NULL,
                planned_minutes INTEGER NOT NULL,
                actual_minutes INTEGER NOT NULL,
                planned_start TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# アプリ起動時にテーブルを準備
init_db()

# ----------------------
# データ保存関数
# ----------------------
def save_data(study_date, planned, actual, planned_start):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO study_log
                (study_date, planned_minutes, actual_minutes, planned_start)
            VALUES (?, ?, ?, ?)
            """,
            (study_date, planned, actual, planned_start)
        )
        conn.commit()

# ----------------------
# データ取得関数
# ----------------------
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM study_log ORDER BY study_date, created_at",
            conn
        )

# ----------------------
# タイトル
# ----------------------
st.title("📚 学習時間トラッカー")
st.write("目標と実際の差を見える化しよう！")

# ----------------------
# 入力フォーム
# ----------------------
st.header("📝 今日の学習記録")

col1, col2 = st.columns(2)

with col1:
    study_date = st.date_input("日付", date.today())
    planned_hours = st.number_input("予定学習時間（時間）", min_value=0.0, step=0.5)
    planned_start = st.time_input("学習開始予定時刻", time(19, 0))

with col2:
    actual_hours = st.number_input("実際の学習時間（時間）", min_value=0.0, step=0.5)

if st.button("記録する"):
    save_data(
        str(study_date),
        int(planned_hours * 60),
        int(actual_hours * 60),
        planned_start.strftime("%H:%M")
    )
    st.success("記録を保存しました！")

# ----------------------
# データ表示
# ----------------------
st.header("📊 学習履歴")

df = load_data()

if not df.empty:
    df["study_date"] = pd.to_datetime(df["study_date"])
    df["planned_datetime"] = pd.to_datetime(
        df["study_date"].dt.strftime("%Y-%m-%d") + " " + df["planned_start"]
    )
    df["planned_hours"] = df["planned_minutes"] / 60
    df["actual_hours"] = df["actual_minutes"] / 60
    df["difference"] = df["actual_hours"] - df["planned_hours"]

    df_display = df[
        ["planned_datetime", "planned_hours", "actual_hours", "difference"]
    ].copy()
    df_display.columns = ["予定日時", "予定時間(h)", "実績時間(h)", "差分(h)"]

    st.dataframe(df_display, use_container_width=True)

    st.subheader("目標 vs 実際")
    st.line_chart(df.set_index("study_date")[["planned_hours", "actual_hours"]])

    st.subheader("目標との差")
    st.bar_chart(df.set_index("study_date")["difference"])
else:
    st.info("まだデータがありません")

# ----------------------
# 学習リマインダー
# ----------------------
st.header("⏰ 学習リマインダー")
st.write("このページを開いている間、予定時刻になると通知します")

# ブラウザー通知の許可をリクエスト
st.components.v1.html("""
<script>
if ("Notification" in window && Notification.permission !== "granted") {
    Notification.requestPermission();
}
</script>
""", height=0)

# 今日の最新の学習予定をSQLite3から取得
today_str = str(date.today())

with sqlite3.connect(DB_PATH) as conn:
    today_record = conn.execute(
        """
        SELECT planned_start
        FROM study_log
        WHERE study_date = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (today_str,)
    ).fetchone()

if today_record:
    planned_time_str = today_record[0]
    planned_dt = datetime.strptime(
        today_str + " " + planned_time_str,
        "%Y-%m-%d %H:%M"
    )
    now = datetime.now()

    if now < planned_dt:
        wait_seconds = int((planned_dt - now).total_seconds())
        st.write(f"次の通知まで約 {wait_seconds // 60} 分")

        st.components.v1.html(f"""
        <script>
        if ("Notification" in window && Notification.permission === "granted") {{
            setTimeout(function() {{
                new Notification("学習時間です！📚", {{
                    body: "予定していた学習を始めましょう！"
                }});
            }}, {wait_seconds * 1000});
        }}
        </script>
        """, height=0)
    else:
        st.info("今日の通知時刻は過ぎています")
else:
    st.info("今日はまだ予定が登録されていません")
