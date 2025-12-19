import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# ============================
# ファイル定義
# ============================
LOG_FILE = "nutrition_log.csv"
FOOD_FILE = "food_db.csv"
UNITS = ["g", "枚", "個", "mL", "大さじ", "小さじ"]

# ============================
# データ読み込み
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
        df = pd.read_csv(FOOD_FILE)
    except:
        df = pd.DataFrame(columns=["food", "unit", "kcal", "protein", "fat", "carbs"])

    if "unit" not in df.columns:
        df["unit"] = "g"

    return df

def save_food_db(df):
    df.to_csv(FOOD_FILE, index=False)

# ============================
# UI
# ============================
st.title("PFC・カロリー自動計算アプリ")

if "page" not in st.session_state:
    st.session_state.page = "main"

col1, col2, col3, col4 = st.columns(4)
if col1.button("メイン画面"):
    st.session_state.page = "main"
if col2.button("食品DB"):
    st.session_state.page = "food"
if col3.button("週間レポート"):
    st.session_state.page = "weekly"
if col4.button("月間レポート"):
    st.session_state.page = "monthly"

data = load_log()
food_db = load_food_db()

# ============================
# 週間レポート
# ============================
if st.session_state.page == "weekly":
    st.header("週間レポート")

    if data.empty:
        st.info("データがありません")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=6)

    week_data = data[data["date"] >= pd.to_datetime(week_ago)]
    daily = week_data.groupby("date").sum()

    st.subheader("1週間合計")
    st.write(daily.sum())

    st.subheader("1日平均")
    st.write(daily.mean())

    st.subheader("推移グラフ")
    st.line_chart(daily[["kcal", "protein", "fat", "carbs"]])

    st.stop()

# ============================
# 月間レポート
# ============================
if st.session_state.page == "monthly":
    st.header("月間レポート")

    if data.empty:
        st.info("データがありません")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    this_month = datetime.date.today().replace(day=1)

    month_data = data[data["date"] >= pd.to_datetime(this_month)]
    daily = month_data.groupby("date").sum()

    st.subheader("今月合計")
    st.write(daily.sum())

    st.subheader("1日平均")
    st.write(daily.mean())

    st.subheader("推移グラフ")
    st.line_chart(daily[["kcal", "protein", "fat", "carbs"]])

    st.stop()

# ============================
# 食品データベース画面
# ============================
if st.session_state.page == "food":
    st.header("食品データベース管理")

    st.subheader("食品の登録")
    new_food = st.text_input("食品名", key="new_food_name")
    new_unit = st.selectbox("単位", UNITS, key="new_food_unit")

    f_k = st.number_input("1単位あたりのカロリー", min_value=0.0, key="new_kcal")
    f_p = st.number_input("1単位あたりのたんぱく質", min_value=0.0, key="new_protein")
    f_f = st.number_input("1単位あたりの脂質", min_value=0.0, key="new_fat")
    f_c = st.number_input("1単位あたりの炭水化物", min_value=0.0, key="new_carbs")

    if st.button("食品を追加"):
        row = pd.DataFrame([[new_food, new_unit, f_k, f_p, f_f, f_c]],
                           columns=food_db.columns)
        food_db = pd.concat([food_db, row], ignore_index=True)
        save_food_db(food_db)
        st.success(f"{new_food} を追加しました")

    st.subheader("登録済み食品一覧")
    st.dataframe(food_db)

    st.subheader("食品データの編集・削除")
    if not food_db.empty:
        edit_food = st.selectbox(
            "編集する食品",
            food_db["food"].unique(),
            key="edit_food_select"
        )

        row = food_db[food_db["food"] == edit_food].iloc[0]

        e_unit = st.selectbox(
            "単位",
            UNITS,
            index=UNITS.index(row["unit"]),
            key=f"edit_unit_{edit_food}"
        )

        e_k = st.number_input("1単位あたりのカロリー", value=float(row["kcal"]), key=f"edit_k_{edit_food}")
        e_p = st.number_input("1単位あたりのたんぱく質", value=float(row["protein"]), key=f"edit_p_{edit_food}")
        e_f = st.number_input("1単位あたりの脂質", value=float(row["fat"]), key=f"edit_f_{edit_food}")
        e_c = st.number_input("1単位あたりの炭水化物", value=float(row["carbs"]), key=f"edit_c_{edit_food}")

        col1, col2 = st.columns(2)

        if col1.button("内容を更新", key=f"update_{edit_food}"):
            food_db.loc[food_db["food"] == edit_food,
                        ["unit", "kcal", "protein", "fat", "carbs"]] = \
                        [e_unit, e_k, e_p, e_f, e_c]
            save_food_db(food_db)
            st.success("更新しました")
            st.experimental_rerun()

        if col2.button("食品を削除", key=f"delete_{edit_food}"):
            food_db = food_db[food_db["food"] != edit_food]
            save_food_db(food_db)
            st.warning("削除しました")
            st.experimental_rerun()

    st.stop()


# ============================
# メイン画面（既存）
# ============================
st.header("今日の食事入力")

if "meals" not in st.session_state:
    st.session_state.meals = {
        "朝": {"kcal":0, "protein":0, "fat":0, "carbs":0},
        "昼": {"kcal":0, "protein":0, "fat":0, "carbs":0},
        "夜": {"kcal":0, "protein":0, "fat":0, "carbs":0},
    }

if "foods_added" not in st.session_state:
    st.session_state.foods_added = {"朝":[], "昼":[], "夜":[]}

if not food_db.empty:
    search = st.text_input("食品検索")
    filtered = food_db[food_db["food"].str.contains(search, case=False, na=False)]

    if not filtered.empty:
        food = st.selectbox("食品選択", filtered["food"])
        row = filtered[filtered["food"] == food].iloc[0]

        amount = st.number_input(f"量（{row['unit']}）", min_value=0.0)

        calc = {
            "kcal": row["kcal"] * amount,
            "protein": row["protein"] * amount,
            "fat": row["fat"] * amount,
            "carbs": row["carbs"] * amount,
        }

        for meal in ["朝", "昼", "夜"]:
            if st.button(f"{meal}に追加"):
                for k in calc:
                    st.session_state.meals[meal][k] += calc[k]
                st.session_state.foods_added[meal].append(f"{food} {amount}{row['unit']}")

# ============================
# 累積表示
# ============================
st.subheader("今日の合計")
for meal in ["朝", "昼", "夜"]:
    st.markdown(f"### {meal}")
    st.write(st.session_state.meals[meal])
    for f in st.session_state.foods_added[meal]:
        st.write("・", f)

# ============================
# 保存
# ============================
if st.button("CSVに保存"):
    today = datetime.date.today().isoformat()
    rows = []
    for meal, v in st.session_state.meals.items():
        rows.append([today, meal, v["kcal"], v["protein"], v["fat"], v["carbs"]])

    data = pd.concat([data, pd.DataFrame(rows, columns=data.columns)])
    save_log(data)
    st.success("保存しました")

# ============================
# グラフ
# ============================
if not data.empty:
    summary = data.groupby("date").sum()
    st.line_chart(summary[["kcal", "protein", "fat", "carbs"]])
