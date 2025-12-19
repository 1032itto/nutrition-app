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
        df = pd.DataFrame(columns=["food", "unit", "kcal", "protein", "fat", "carbs", "favorite"])

    # unit補正
    df["unit"] = df.get("unit", "100g").replace({
        "g": "100g",
        "ml": "100mL",
        "mL": "100mL"
    })

    # favorite補正
    if "favorite" not in df.columns:
        df["favorite"] = False

    #　数値列を強制float化
    for col in ["kcal", "protein", "fat", "carbs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

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
    
    required_cols = ["food","unit","kcal","protein","fat","carbs","favorite"]
    for c in required_cols:
        if c not in food_db.columns:
            food_db[c] = False if c == "favorite" else 0


    # --- 新規登録 ---
    st.subheader("食品登録")
    new_food = st.text_input("食品名")
    new_unit = st.selectbox("単位", UNITS, key="new_unit_select")
    per_label = f"{new_unit}あたり" if new_unit in ["100g", "100mL"] else f"1{new_unit}あたり"


    f_k = st.number_input(f"{per_label}のカロリー", min_value=0.0)
    f_p = st.number_input(f"{per_label}のたんぱく質", min_value=0.0)
    f_f = st.number_input(f"{per_label}の脂質", min_value=0.0)
    f_c = st.number_input(f"{per_label}の炭水化物", min_value=0.0)


    if st.button("食品を追加") and new_food:
        row = pd.DataFrame([{
            "food": new_food,
            "unit": new_unit,
            "kcal": f_k,
            "protein": f_p,
            "fat": f_f,
            "carbs": f_c,
            "favorite": False
        }])

        food_db = pd.concat([food_db, row], ignore_index=True)
        food_db.to_csv(FOOD_FILE, index=False)
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
    
    # --- 食品DB一覧 ---

    st.subheader("食品DB")

    # favorite列が無ければ追加
    if "favorite" not in food_db.columns:
        food_db["favorite"] = False
        food_db.to_csv(FOOD_FILE, index=False)

    with st.expander("食品DB一覧（検索・編集・削除）", expanded=False):

        if food_db.empty:
            st.info("食品が登録されていません")
        else:

            # =========================
            # 検索
            # =========================
            keyword = st.text_input("食品名で検索", key="food_search")

            view_df = food_db.copy()

            if keyword:
                view_df = view_df[view_df["food"].str.contains(keyword, case=False)]

            # =========================
            # お気に入りを上に
            # =========================
            view_df = view_df.sort_values("favorite", ascending=False)

            if view_df.empty:
                st.info("該当する食品がありません")
            else:
                # =========================
                # 一覧表示
                # =========================
                for idx, row in view_df.iterrows():

                    with st.container():
                        cols = st.columns([3, 2, 2, 2, 2, 2, 1, 1, 1])

                        # --- 表示用基準量 ---
                        base_label = (
                            f"{row['unit']}あたり"
                            if row["unit"] in ["100g", "100mL"]
                            else f"1{row['unit']}あたり"
                        )

                        cols[0].markdown(f"**{row['food']}**")
                        cols[1].write(base_label)
                        cols[2].write(f"{row['kcal']} kcal")
                        cols[3].write(f"P {row['protein']} g")
                        cols[4].write(f"F {row['fat']} g")
                        cols[5].write(f"C {row['carbs']} g")

                        # お気に入り
                        fav_label = "★" if row["favorite"] else "☆"
                        fav = cols[6].button(
                            fav_label,
                            key=f"fav_{idx}"
                        )

                        # ✏ 編集
                        edit = cols[7].button("✏", key=f"edit_{idx}")

                        # 🗑 削除
                        delete = cols[8].button("🗑", key=f"del_{idx}")

                        # =========================
                        # お気に入り更新
                        # =========================
                        if fav != row["favorite"]:
                            food_db.loc[idx, "favorite"] = fav
                            food_db.to_csv(FOOD_FILE, index=False)
                            st.rerun()

                        # =========================
                        # 削除
                        # =========================
                        if delete:
                            food_db = food_db.drop(idx)
                            food_db = food_db.reset_index(drop=True)
                            food_db.to_csv(FOOD_FILE, index=False)
                            st.rerun()

                        # =========================
                        # 編集
                        # =========================
                        if edit:
                            st.session_state.edit_index = idx

                # =========================
                # 編集フォーム
                # =========================
                if "edit_index" in st.session_state:
                    i = st.session_state.edit_index
                    row = food_db.loc[i]

                    st.divider()
                    st.markdown("### 食品を編集")

                    e_food = st.text_input("食品名", row["food"], key="e_food")
                    # unit が UNITS に無い場合は先頭を選択
                    unit_index = UNITS.index(row["unit"]) if row["unit"] in UNITS else 0

                    e_unit = st.selectbox(
                        "単位",
                        UNITS,
                        index=unit_index,
                        key="e_unit"
                    )
                    e_kcal = st.number_input(f"{per_label}のカロリー", value=float(row["kcal"] or 0))
                    e_p = st.number_input(f"{per_label}のたんぱく質", value=float(row["protein"] or 0))
                    e_f = st.number_input(f"{per_label}の脂質", value=float(row["fat"] or 0))
                    e_c = st.number_input(f"{per_label}の炭水化物", value=float(row["carbs"] or 0))
                    t.number_input("炭水化物", value=float(row["carbs"]), key="e_c")

                    col1, col2 = st.columns(2)

                    if col1.button("保存"):
                        food_db.loc[i] = [
                            e_food, e_unit, e_kcal, e_p, e_f, e_c, row["favorite"]
                        ]
                        food_db = food_db.reset_index(drop=True)
                        food_db.to_csv(FOOD_FILE, index=False)
                        del st.session_state.edit_index
                        st.rerun()

                    if col2.button("キャンセル"):
                        del st.session_state.edit_index
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
    calc = {
        k: float(row[k]) * factor
        for k in ["kcal", "protein", "fat", "carbs"]
    }

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
