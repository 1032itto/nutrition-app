
import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt

st.title("1日のPFC・カロリー記録アプリ")

# CSV保存用ファイル
FILE = "nutrition_log.csv"

# データ読み込み
def load_data():
    try:
        return pd.read_csv(FILE)
    except:
        return pd.DataFrame(columns=["date", "meal", "kcal", "protein", "fat", "carbs"])

# データ保存
def save_data(df):
    df.to_csv(FILE, index=False)

# 入力UI
def meal_input(meal_name):
    st.subheader(meal_name)
    kcal = st.number_input(f"{meal_name}のカロリー", min_value=0.0, step=1.0, key=f"kcal_{meal_name}")
    p = st.number_input(f"{meal_name}のタンパク質 (g)", min_value=0.0, step=0.1, key=f"p_{meal_name}")
    f = st.number_input(f"{meal_name}の脂質 (g)", min_value=0.0, step=0.1, key=f"f_{meal_name}")
    c = st.number_input(f"{meal_name}の炭水化物 (g)", min_value=0.0, step=0.1, key=f"c_{meal_name}")
    return kcal, p, f, c

st.header("食品データベース")

# 食品データベースの読み込み・保存
FOOD_FILE = "food_db.csv"

def load_food():
    try:
        return pd.read_csv(FOOD_FILE)
    except:
        return pd.DataFrame(columns=["food", "kcal", "protein", "fat", "carbs"])

def save_food(df):
    df.to_csv(FOOD_FILE, index=False)

food_db = load_food()

st.subheader("食品の登録")
new_food = st.text_input("食品名")
f_k = st.number_input("100gあたりのカロリー", min_value=0.0)
f_p = st.number_input("100gあたりのタンパク質", min_value=0.0)
f_f = st.number_input("100gあたりの脂質", min_value=0.0)
f_c = st.number_input("100gあたりの炭水化物", min_value=0.0)

if st.button("食品を追加"):
    row = pd.DataFrame([[new_food, f_k, f_p, f_f, f_c]], columns=food_db.columns)
    food_db = pd.concat([food_db, row], ignore_index=True)
    save_food(food_db)
    st.success("登録しました！")

st.dataframe(food_db)

st.header("今日の食事入力")

st.subheader("食品から入力する")

if not food_db.empty:
    selected_food = st.selectbox("食品を選択", food_db["food"].unique())
    amount = st.number_input("食べた量(g)", min_value=0.0, step=10.0)

    if st.button("計算して朝に追加"):
        row = food_db[food_db["food"] == selected_food].iloc[0]
        b_kcal = row["kcal"] * amount / 100
        b_p = row["protein"] * amount / 100
        b_f = row["fat"] * amount / 100
        b_c = row["carbs"] * amount / 100
        st.success(f"朝に {selected_food} を追加しました！")

    if st.button("計算して昼に追加"):
        row = food_db[food_db["food"] == selected_food].iloc[0]
        l_kcal = row["kcal"] * amount / 100
        l_p = row["protein"] * amount / 100
        l_f = row["fat"] * amount / 100
        l_c = row["carbs"] * amount / 100
        st.success(f"昼に {selected_food} を追加しました！")

    if st.button("計算して夜に追加"):
        row = food_db[food_db["food"] == selected_food].iloc[0]
        d_kcal = row["kcal"] * amount / 100
        d_p = row["protein"] * amount / 100
        d_f = row["fat"] * amount / 100
        d_c = row["carbs"] * amount / 100
        st.success(f"夜に {selected_food} を追加しました！")
else:
    st.warning("食品データベースが空です。先に登録して下さい。")

date = datetime.date.today().isoformat()

# 入力エリア
b_kcal, b_p, b_f, b_c = meal_input("朝")
l_kcal, l_p, l_f, l_c = meal_input("昼")
d_kcal, d_p, d_f, d_c = meal_input("夜")

# 保存ボタン
data = load_data()

if st.button("保存する"):
    new_rows = [
        [date, "朝", b_kcal, b_p, b_f, b_c],
        [date, "昼", l_kcal, l_p, l_f, l_c],
        [date, "夜", d_kcal, d_p, d_f, d_c],
    ]
    new_df = pd.DataFrame(new_rows, columns=data.columns)
    data = pd.concat([data, new_df], ignore_index=True)
    save_data(data)
    st.success("保存しました！")

# データ表示
st.header("記録一覧")
st.dataframe(data)

# AIアドバイス生成
st.header("AIアドバイス")

def generate_advice(row):
    advice = []
    if row["protein"] < 1.6 * 59:  # 体重59kgとして例示
        advice.append("タンパク質が少なめです。もう1品プロテイン源を追加すると良いです。")
    if row["fat"] > 60:
        advice.append("脂質が多めです。揚げ物や油の量を少し減らすとバランスが良くなります。")
    if row["carbs"] < 200:
        advice.append("炭水化物が少ないのでトレーニング効率が落ちる可能性があります。軽く追加しましょう。")
    if not advice:
        advice.append("良いバランスです。この調子です！")
    return "".join(advice)

day_summary = data.groupby("date").sum()
if not day_summary.empty:
    today = datetime.date.today().isoformat()
    if today in day_summary.index:
        today_row = day_summary.loc[today]
        st.write(generate_advice(today_row))
    else:
        st.write("今日の記録がまだありません。入力してください。")

# グラフ化
st.header("1日の合計PFCグラフ")

day_summary = data.groupby("date").sum()

if not day_summary.empty:
    st.line_chart(day_summary[["kcal", "protein", "fat", "carbs"]])
else:
    st.write("データがありません")
