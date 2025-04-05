import streamlit as st
import pandas as pd
import os

# データ保存用ファイル名
DATA_FILE = "household_data.csv"

# 初期化：データファイルが存在しない場合は作成する
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["Person", "Date", "Amount"]).to_csv(DATA_FILE, index=False)


# データ読み込み
def load_data():
    return pd.read_csv(DATA_FILE)


# データ保存
def save_data(data):
    data.to_csv(DATA_FILE, index=False)


# アプリのタイトル
st.title("家計管理アプリ")

# データの読み込み
data = load_data()

# 入力フォーム
st.header("支出の記録")
col1, col2 = st.columns(2)

with col1:
    st.subheader("たく")
    person_1_date = st.date_input("日付（たく）")
    person_1_amount = st.number_input("金額（たく）", min_value=0, step=100)
    if st.button("追加（たく）"):
        new_row = {
            "Person": "たく",
            "Date": str(person_1_date),
            "Amount": person_1_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(data)
        st.success("たく の支出が追加されました！")

with col2:
    st.subheader("めい")
    person_2_date = st.date_input("日付（めい）")
    person_2_amount = st.number_input("金額（めい）", min_value=0, step=100)
    if st.button("追加（めい）"):
        new_row = {
            "Person": "めい",
            "Date": str(person_2_date),
            "Amount": person_2_amount,
        }
        data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(data)
        st.success("めい の支出が追加されました！")

# 表の表示
st.header("支出一覧")
st.dataframe(data)

# 精算機能
st.header("精算")
if st.button("精算する"):
    # Personごとの合計金額を計算
    total_person_1 = data[data["Person"] == "たく"]["Amount"].sum()
    total_person_2 = data[data["Person"] == "めい"]["Amount"].sum()

    # 精算計算
    total_spent = total_person_1 + total_person_2
    equal_share = total_spent / 2
    difference = total_person_1 - total_person_2

    if difference > 0:
        payer = "めい"
        payee = "たく"
        amount_to_pay = abs(difference) / 2
    elif difference < 0:
        payer = "たく"
        payee = "めい"
        amount_to_pay = abs(difference) / 2
    else:
        payer, payee, amount_to_pay = None, None, None

    # 結果表示
    if payer and payee:
        st.write(f"{payer} が {payee} に ¥{amount_to_pay:.0f} 支払う必要があります。")
    else:
        st.write("精算する必要はありません。")

    # データクリア
    data = pd.DataFrame(columns=["Person", "Date", "Amount"])
    save_data(data)
    st.success("精算が完了しました！表の内容はクリアされました。")
