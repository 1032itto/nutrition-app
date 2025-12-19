import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# ============================
# ファイル定義
# ============================
LOG_FILE = "nutrition_log.csv"
FOOD_FILE = "food_db.csv"
UNITS = ["100g", "100mL", "枚", "個", "大さじ", "小さじ"]

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
        df["unit"] = "100g"

    # ★ 旧単位の正規化
    df["unit"] = df["unit"].replace({
        "g": "100g",
        "ml": "100mL",
        "mL": "100mL"
    })

    return df

def save_food_db(df):
    df.to_csv(FOOD_FILE, index=False)

# ============================
# UI
# ============================
st.title("PFC・カロリー自動計算アプリ")

if "page" not in st.session_state:
    st.session_state.page = "main"

col1, col2, col3, col4, col5, col6 = st.columns(6)
if col1.button("メイン"):
    st.session_state.page = "main"
if col2.button("食品DB"):
    st.session_state.page = "food"
if col3.button("週間"):
    st.session_state.page = "weekly"
if col4.button("月間"):
    st.session_state.page = "monthly"
if col5.button("履歴"):
    st.session_state.page = "history"
if col6.button("設定"):
    st.session_state.page = "settings"

data = load_log()
food_db = load_food_db()

# ============================
# 目標設定
# ============================
if "targets" not in st.session_state:
    st.session_state.targets = {
        "kcal": 2000.0,
        "protein": 100.0,
        "fat": 60.0,
        "carbs": 250.0
    }

# ============================
# 設定ページ
# ============================
if st.session_state.page == "settings":
    st.header("目標設定")
    t = st.session_state.targets

    t["kcal"] = st.number_input("目標カロリー", value=float(t["kcal"]))
    t["protein"] = st.number_input("目標たんぱく質", value=float(t["protein"]))
    t["fat"] = st.number_input("目標脂質", value=float(t["fat"]))
    t["carbs"] = st.number_input("目標炭水化物", value=float(t["carbs"]))

    st.success("自動保存されます")
    st.stop()

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

    st.subheader("合計")
    st.write(daily.sum())

    st.subheader("平均")
    st.write(daily.mean())

    chart_df = daily[["kcal", "protein", "fat", "carbs"]]
    for k in chart_df.columns:
        chart_df[f"{k}_target"] = st.session_state.targets[k]

    st.line_chart(chart_df)
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
    start = datetime.date.today().replace(day=1)
    month_data = data[data["date"] >= pd.to_datetime(start)]
    daily = month_data.groupby("date").sum(numeric_only=True)

    st.subheader("合計")
    st.write(daily.sum())

    st.subheader("平均")
    st.write(daily.mean())

    chart_df = daily[["kcal", "protein", "fat", "carbs"]]
    for k in chart_df.columns:
        chart_df[f"{k}_target"] = st.session_state.targets[k]

    st.line_chart(chart_df)
    st.stop()

# ============================
# 食品DB管理
# ============================
if st.session_state.page == "food":
    st.header("食品データベース管理")

    # --- 新規登録 ---
    st.subheader("食品登録")
    new_food = st.text_input("食品名")
    new_unit = st.selectbox("単位", UNITS, key="new_unit_select")
    per_label = f"{new_unit}あたり" if new_unit in ["100g", "100mL"] else f"1{new_unit}あたり"


    f_k = st.number_input(f"{per_label}のカロリー", min_value=0.0)
    f_p = st.number_input(f"{per_label}のたんぱく質", min_value=0.0)
    f_f = st.number_input(f"{per_label}の脂質", min_value=0.0)
    f_c = st.number_input(f"{per_label}の炭水化物", min_value=0.0)


    if st.button("追加") and new_food:
        food_db = pd.concat([
            food_db,
            pd.DataFrame([[new_food, new_unit, f_k, f_p, f_f, f_c]],
                         columns=food_db.columns)
        ], ignore_index=True)
        save_food_db(food_db)
        st.success("追加しました")
        st.rerun()

    st.divider()

    # --- 編集・削除（検索付き） ---
    st.subheader("編集・削除")
    search_edit = st.text_input("食品検索")

    filtered = food_db[food_db["food"].str.contains(search_edit, case=False, na=False)]
    if filtered.empty:
        st.info("該当食品なし")
        st.stop()

    edit_food = st.selectbox("食品選択", filtered["food"])
    row = filtered[filtered["food"] == edit_food].iloc[0]

    unit_index = UNITS.index(row["unit"]) if row["unit"] in UNITS else 0
    e_unit = st.selectbox("単位", UNITS, index=unit_index, key="edit_unit_select")
    
    per_label = f"{e_unit}あたり" if e_unit in ["100g", "100mL"] else f"1{e_unit}あたり"


    e_k = st.number_input(f"{per_label}のカロリー", value=float(row["kcal"]))
    e_p = st.number_input(f"{per_label}のたんぱく質", value=float(row["protein"]))
    e_f = st.number_input(f"{per_label}の脂質", value=float(row["fat"]))
    e_c = st.number_input(f"{per_label}の炭水化物", value=float(row["carbs"]))


    c1, c2 = st.columns(2)
    if c1.button("更新"):
        food_db.loc[food_db["food"] == edit_food,
                    ["unit", "kcal", "protein", "fat", "carbs"]] = \
            [e_unit, e_k, e_p, e_f, e_c]
        save_food_db(food_db)
        st.success("更新しました")
        st.rerun()

    if c2.button("削除"):
        food_db = food_db[food_db["food"] != edit_food]
        save_food_db(food_db)
        st.warning("削除しました")
        st.rerun()

    st.stop()

# ============================
# 履歴閲覧
# ============================
if st.session_state.page == "history":
    st.header("履歴閲覧")
    if data.empty:
        st.info("記録なし")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    d = st.date_input("日付", data["date"].max().date())
    day = data[data["date"] == pd.to_datetime(d)]

    if day.empty:
        st.info("この日の記録なし")
    else:
        st.dataframe(day)
        st.write(day[["kcal", "protein", "fat", "carbs"]].sum())
    st.stop()

# ============================
# メイン画面
# ============================
st.header("食事入力")
selected_date = st.date_input("記録日", datetime.date.today())

if "meals" not in st.session_state:
    st.session_state.meals = {m: {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
                              for m in ["朝", "昼", "夜"]}
if "foods_added" not in st.session_state:
    st.session_state.foods_added = {m: [] for m in ["朝", "昼", "夜"]}

search = st.text_input("食品検索")
filtered = food_db[food_db["food"].str.contains(search, case=False, na=False)]

if not filtered.empty:
    food = st.selectbox("食品", filtered["food"])
    row = filtered[filtered["food"] == food].iloc[0]

    disp_unit = "g" if row["unit"] == "100g" else "mL" if row["unit"] == "100mL" else row["unit"]
    amount = st.number_input(f"量（{disp_unit}）", min_value=0.0)
    meal = st.selectbox("食事区分", ["朝", "昼", "夜"])

    factor = amount / 100 if row["unit"] in ["100g", "100mL"] else amount
    calc = {k: row[k] * factor for k in ["kcal", "protein", "fat", "carbs"]}

    if st.button("追加"):
        st.session_state.foods_added[meal].append(
            {"food": food, "amount": amount, "unit": disp_unit, **calc}
        )
        for k in calc:
            st.session_state.meals[meal][k] += calc[k]

# ============================
# 表示・削除
# ============================
st.subheader("当日の記録")
for meal in ["朝", "昼", "夜"]:
    st.markdown(f"### {meal}")
    for i, f in enumerate(st.session_state.foods_added[meal]):
        c1, c2 = st.columns([4, 1])
        c1.write(f"{f['food']} {f['amount']}{f['unit']} ({f['kcal']:.0f}kcal)")
        if c2.button("削除", key=f"{meal}_{i}"):
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
