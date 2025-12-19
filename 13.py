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
        return pd.DataFrame(columns=[
            "date", "meal", "food", "amount",
            "kcal", "protein", "fat", "carbs"
        ])


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
if col4.button("履歴閲覧"):
    st.session_state.page = "history"

data = load_log()

# ============================
# 目標設定
# ============================
if "targets" not in st.session_state:
    st.session_state.targets = {"kcal":2000.0, "protein":100.0, "fat":60.0, "carbs":250.0}
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
    daily = week_data.groupby("date").sum(numeric_only=True)

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
    daily = month_data.groupby("date").sum(numeric_only=True)

    st.subheader("今月合計")
    st.write(daily.sum())

    st.subheader("1日平均")
    st.write(daily.mean())

    st.subheader("推移グラフ")
    st.line_chart(daily[["kcal", "protein", "fat", "carbs"]])

    st.stop()

# ============================
# 食品DB画面（編集・削除対応）
# ============================
if st.session_state.page == "food":
    st.header("食品データベース管理")

    # --- 新規登録 ---
    st.subheader("食品の登録")
    new_food = st.text_input("食品名", key="new_food")
    new_unit = st.selectbox("単位", UNITS, key="new_unit")
    f_k = st.number_input("1単位あたりのカロリー", min_value=0.0, key="new_k")
    f_p = st.number_input("1単位あたりのたんぱく質", min_value=0.0, key="new_p")
    f_f = st.number_input("1単位あたりの脂質", min_value=0.0, key="new_f")
    f_c = st.number_input("1単位あたりの炭水化物", min_value=0.0, key="new_c")

    if st.button("食品を追加") and new_food:
        row = pd.DataFrame([[new_food, new_unit, f_k, f_p, f_f, f_c]], columns=food_db.columns)
        food_db = pd.concat([food_db, row], ignore_index=True)
        save_food_db(food_db)
        st.success("追加しました")
        st.rerun()

    st.divider()

    # --- 編集・削除 ---
    st.subheader("登録済み食品の編集・削除")
    if not food_db.empty:
        edit_food = st.selectbox("食品選択", food_db["food"], key="edit_food")
        row = food_db[food_db["food"] == edit_food].iloc[0]

        e_unit = st.selectbox("単位", UNITS, index=UNITS.index(row["unit"]))
        e_k = st.number_input("カロリー", value=float(row["kcal"]))
        e_p = st.number_input("たんぱく質", value=float(row["protein"]))
        e_f = st.number_input("脂質", value=float(row["fat"]))
        e_c = st.number_input("炭水化物", value=float(row["carbs"]))

        col1, col2 = st.columns(2)
        if col1.button("更新"):
            food_db.loc[food_db["food"] == edit_food, ["unit", "kcal", "protein", "fat", "carbs"]] = \
                [e_unit, e_k, e_p, e_f, e_c]
            save_food_db(food_db)
            st.success("更新しました")
            st.rerun()

        if col2.button("削除"):
            food_db = food_db[food_db["food"] != edit_food]
            save_food_db(food_db)
            st.warning("削除しました")
            st.rerun()

    st.stop()

# ============================
# 履歴閲覧ページ
# ============================
if st.session_state.page == "history":
    st.header("過去の記録閲覧")
    if data.empty:
        st.info("記録がありません")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    view_date = st.date_input("閲覧する日付", data["date"].max().date())
    day = data[data["date"] == pd.to_datetime(view_date)]

    if day.empty:
        st.info("この日の記録はありません")
    else:
        st.dataframe(day)
        st.subheader("合計")
        st.write(day[["kcal","protein","fat","carbs"]].sum())
    st.stop()

# ============================
# メイン画面
# ============================
st.header("食事入力")

selected_date = st.date_input("記録する日付", datetime.date.today())

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
        meal = st.selectbox("食事区分", ["朝", "昼", "夜"])

        calc = {
            "kcal": row["kcal"] * amount,
            "protein": row["protein"] * amount,
            "fat": row["fat"] * amount,
            "carbs": row["carbs"] * amount,
        }

        if st.button("追加"):
            st.session_state.foods_added[meal].append({
                "food": food,
                "amount": amount,
                "unit": row["unit"],
                **calc
            })
            for k in calc:
                st.session_state.meals[meal][k] += calc[k]

# ============================
# 当日の表示・削除
# ============================
st.subheader("その日の記録")

for meal in ["朝", "昼", "夜"]:
    st.markdown(f"### {meal}")

    for i, f in enumerate(st.session_state.foods_added[meal]):
        col1, col2 = st.columns([4,1])
        with col1:
            st.write(f"{f['food']} {f['amount']}{f['unit']} ({f['kcal']:.0f}kcal)")
        with col2:
            if st.button("削除", key=f"del_{meal}_{i}"):
                for k in ["kcal", "protein", "fat", "carbs"]:
                    st.session_state.meals[meal][k] -= f[k]
                st.session_state.foods_added[meal].pop(i)
                st.rerun()

    st.write(st.session_state.meals[meal])

# ============================
# 保存
# ============================
if st.button("CSVに保存"):
    rows = []
    for meal, foods in st.session_state.foods_added.items():
        for f in foods:
            rows.append([
                selected_date.isoformat(), meal,
                f["food"], f["amount"],
                f["kcal"], f["protein"], f["fat"], f["carbs"]
            ])

    data = pd.concat([data, pd.DataFrame(rows, columns=data.columns)])
    save_log(data)
    st.success("保存しました")
    st.rerun()