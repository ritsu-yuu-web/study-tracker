import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, time
import time as t

st.set_page_config(page_title="学習時間トラッカー", layout="wide")

# ----------------------
# DBセットアップ
# ----------------------
conn = sqlite3.connect("study_data.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS study_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_date TEXT,
    planned_minutes INTEGER,
    actual_minutes INTEGER,
    planned_start TEXT
)
""")
conn.commit()

# ----------------------
# データ取得関数
# ----------------------
def load_data():
    df = pd.read_sql("SELECT * FROM study_log", conn)
    return df

def save_data(study_date, planned, actual, planned_start):
    c.execute(
        "INSERT INTO study_log (study_date, planned_minutes, actual_minutes, planned_start) VALUES (?, ?, ?, ?)",
        (study_date, planned, actual, planned_start)
    )
    conn.commit()

# ----------------------
# タイトル
# ----------------------
st.title("📚 学習時間トラッカー")
st.write("予定と実績の差を見える化しよう！")

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
    df["planned_hours"] = df["planned_minutes"] / 60
    df["actual_hours"] = df["actual_minutes"] / 60
    df["difference"] = df["actual_hours"] - df["planned_hours"]

    st.dataframe(df[["study_date", "planned_hours", "actual_hours", "difference"]])

    st.subheader("予定 vs 実績")
    st.line_chart(df.set_index("study_date")[["planned_hours", "actual_hours"]])

    st.subheader("実績 − 予定（差分）")
    st.bar_chart(df.set_index("study_date")["difference"])

else:
    st.info("まだデータがありません")

# ----------------------
# 🔔 通知機能
# ----------------------
st.header("⏰ 学習リマインダー")

st.write("このページを開いている間、予定時刻になると通知します")

# 通知許可用JS
st.components.v1.html("""
<script>
function requestNotificationPermission() {
    if (Notification.permission !== "granted") {
        Notification.requestPermission();
    }
}
requestNotificationPermission();
</script>
""", height=0)

if not df.empty:
    today_str = str(date.today())
    today_data = df[df["study_date"] == pd.to_datetime(today_str)]

    if not today_data.empty:
        planned_time_str = today_data.iloc[-1]["planned_start"]
        planned_dt = datetime.strptime(today_str + " " + planned_time_str, "%Y-%m-%d %H:%M")

        now = datetime.now()

        if now < planned_dt:
            wait_seconds = (planned_dt - now).total_seconds()
            st.write(f"次の通知まで約 {int(wait_seconds//60)} 分")

            # 自動リロード用
            st.experimental_singleton.clear()
            t.sleep(1)

            st.components.v1.html(f"""
            <script>
            setTimeout(function() {{
                new Notification("学習時間です！📚", {{
                    body: "予定していた学習を始めましょう！"
                }});
            }}, {int(wait_seconds * 1000)});
            </script>
            """, height=0)
        else:
            st.info("今日の通知時刻は過ぎています")
    else:
        st.info("今日はまだ予定が登録されていません")
