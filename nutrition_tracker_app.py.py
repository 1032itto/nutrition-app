import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# ============================
# ファイル定義
# ============================
LOG_FILE = "nutrition_log.csv"
FOOD_FILE = "food_db.csv"

# ============================
# データ読み込み関数
# ============================
def load_log():
    try:
        return pd.read_csv(LOG_FILE)
    except:
        return pd.DataFrame(columns=["date", "meal", "kcal", "protein", "fat", "carbs"])

def save_log(df):
    df.to_csv(LOG_FILE, index=False)


def load_food_db():
    try:
        return pd.read_csv(FOOD_FILE)
    except:
        return pd.DataFrame(columns=["food", "kcal", "protein", "fat", "carbs"])

def save_food_db(df):
    df.to_csv(FOOD_FILE, index=False)

# ============================
# Streamlit UI
# ============================
st.title("PFC・カロリー自動計算アプリ（完成版）")

data = load_log()
food_db = load_food_db()

# ------------------------------------
# 食品データベース管理
# ------------------------------------
st.header("食品データベース")
st.subheader("食品の登録")

new_food = st.text_input("食品名")
f_k = st.number_input("100gあたりのカロリー", min_value=0.0)
f_p = st.number_input("100gあたりのたんぱく質", min_value=0.0)
f_f = st.number_input("100gあたりの脂質", min_value=0.0)
f_c = st.number_input("100gあたりの炭水化物", min_value=0.0)

if st.button("食品を追加"):
    row = pd.DataFrame([[new_food, f_k, f_p, f_f, f_c]], columns=food_db.columns)
    food_db = pd.concat([food_db, row], ignore_index=True)
    save_food_db(food_db)
    st.success(f"{new_food} を追加しました！")

st.dataframe(food_db)

# ------------------------------------
# 食事の累積記録用変数
# ------------------------------------
if "meals" not in st.session_state:
    st.session_state.meals = {
        "朝": {"kcal":0, "protein":0, "fat":0, "carbs":0},
        "昼": {"kcal":0, "protein":0, "fat":0, "carbs":0},
        "夜": {"kcal":0, "protein":0, "fat":0, "carbs":0},
    }

# ------------------------------------
# 食品から計算して追加
# ------------------------------------
st.header("今日の食事入力")
st.subheader("食品を選んで量を入力 → 自動計算")

if not food_db.empty:
    selected_food = st.selectbox("食品を選択", food_db["food"].unique())
    amount = st.number_input("食べた量(g)", min_value=0.0, step=10.0)

    row = food_db[food_db["food"] == selected_food].iloc[0]
    calc = {
        "kcal": row["kcal"] * amount / 100,
        "protein": row["protein"] * amount / 100,
        "fat": row["fat"] * amount / 100,
        "carbs": row["carbs"] * amount / 100,
    }

    st.write(f"計算結果 : {calc}")

    colA, colB, colC = st.columns(3)

    if colA.button("朝に追加"):
        for k in calc:
            st.session_state.meals["朝"][k] += calc[k]
        st.success(f"朝に {selected_food} を追加しました！")

    if colB.button("昼に追加"):
        for k in calc:
            st.session_state.meals["昼"][k] += calc[k]
        st.success(f"昼に {selected_food} を追加しました！")

    if colC.button("夜に追加"):
        for k in calc:
            st.session_state.meals["夜"][k] += calc[k]
        st.success(f"夜に {selected_food} を追加しました！")
else:
    st.warning("食品データベースが空です。先に食品を登録してください。")

# ------------------------------------
# 今日の累積結果表示
# ------------------------------------
st.subheader("今日の累積PFC")
for meal, vals in st.session_state.meals.items():
    st.write(meal, vals)

# ------------------------------------
# 保存処理
# ------------------------------------
if st.button("CSVに保存する"):
    today = datetime.date.today().isoformat()
    new_rows = []
    for meal, vals in st.session_state.meals.items():
        new_rows.append([today, meal, vals["kcal"], vals["protein"], vals["fat"], vals["carbs"]])

    df_new = pd.DataFrame(new_rows, columns=data.columns)
    data = pd.concat([data, df_new], ignore_index=True)
    save_log(data)

    st.success("保存しました！")

# ------------------------------------
# AIアドバイス
# ------------------------------------
st.header("AI アドバイス")

def generate_advice(row):
    advice = []
    weight = 59  # 必要なら外部設定化

    if row["protein"] < 1.6 * weight:
        advice.append("タンパク質が少なめです。もう1品タンパク質源を追加すると良いです。")
    if row["fat"] > 60:
        advice.append("脂質が多めです。揚げ物を控えると改善します。")
    if row["carbs"] < 200:
        advice.append("炭水化物が少なく、トレーニング効率が落ちる可能性があります。")
    if not advice:
        advice.append("良いバランスです！この調子！")

    return "\n".join(advice)

# 今日の合計
if data.empty:
    st.write("まだ記録がありません。")
else:
    day_summary = data.groupby("date").sum()
    today = datetime.date.today().isoformat()

    if today in day_summary.index:
        st.write(generate_advice(day_summary.loc[today]))

# ------------------------------------
# グラフ
# ------------------------------------
st.header("グラフ表示")

if not data.empty:
    day_summary = data.groupby("date").sum()
    st.line_chart(day_summary[["kcal", "protein", "fat", "carbs"]])
else:
    st.write("データがありません。")