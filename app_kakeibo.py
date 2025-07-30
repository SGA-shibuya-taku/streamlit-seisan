import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import calendar
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io


# 設定を読み込む関数
def load_config():
    """必要な設定のみsecrets.tomlから読み込み、その他は直接定義"""
    app_config = st.secrets.get("APP_CONFIG", {})
    
    config = {
        # アプリケーション設定（固定値）
        "app_title": "家計簿アプリ",
        "page_icon": "",
        "layout": "wide",
        
        # 環境変数から読み込む設定
        "target_folder": app_config.get("target_folder_name", "家計簿"),
        "csv_pattern": app_config.get("csv_filename_pattern",
                                      "record{year_month}.csv"),
        
        # Google Drive設定（固定値）
        "max_files": 20,
        "page_size": 10,
        "csv_mime_types": ["text/csv", "application/csv",
                           "text/plain", "application/vnd.ms-excel"],
        "encodings": ["utf-8", "shift_jis", "cp932", "iso-2022-jp"]
    }
    
    return config


# Google Sheets API認証
def authenticate_google_sheets():
    """Google Sheets APIの認証"""
    try:
        google_credentials = st.secrets["GOOGLE_CREDENTIALS"]
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            google_credentials, scope
        )
        return credentials
    except Exception as e:
        st.error(f"Google認証エラー: {e}")
        return None


def get_drive_service():
    """Google Drive APIサービスを取得"""
    credentials = authenticate_google_sheets()
    if credentials:
        return build('drive', 'v3', credentials=credentials)
    return None


def search_csv_file_in_drive(year_month, drive_service):
    """Google Driveの指定フォルダからrecordyyyyMM.csvファイルを検索"""
    config = load_config()
    filename = config["csv_pattern"].format(year_month=year_month)
    target_folder = config["target_folder"]
    
    try:
        # 指定フォルダを検索
        folder_query = (f"name='{target_folder}' and "
                        f"mimeType='application/vnd.google-apps.folder'")
        folder_results = drive_service.files().list(
            q=folder_query,
            pageSize=config["page_size"],
            fields="nextPageToken, files(id, name)"
        ).execute()
        
        folders = folder_results.get('files', [])
        
        if not folders:
            st.error(f"「{target_folder}」フォルダが見つかりませんでした")
            st.warning("以下を確認してください：")
            st.write(f"1. Google Driveに「{target_folder}」という名前のフォルダが存在するか")
            account_msg = ("2. サービスアカウント "
                           "(kakei-seisan@expanded-flame-426112-n8.iam."
                           "gserviceaccount.com) "
                           "にフォルダの共有権限があるか")
            st.write(account_msg)
            return None
        
        folder_id = folders[0]['id']
        
        # フォルダ内でCSVファイルを検索
        # まずmimeTypeを指定せずに名前のみで検索
        query_name_only = f"name='{filename}' and '{folder_id}' in parents"
        file_results_name = drive_service.files().list(
            q=query_name_only,
            pageSize=config["page_size"],
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        
        files_by_name = file_results_name.get('files', [])
        
        # CSVのmimeTypeで検索（設定から取得）
        files = []
        for mime_type in config["csv_mime_types"]:
            query = (f"name='{filename}' and mimeType='{mime_type}' "
                     f"and '{folder_id}' in parents")
            file_results = drive_service.files().list(
                q=query,
                pageSize=config["page_size"],
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            
            found_files = file_results.get('files', [])
            if found_files:
                files.extend(found_files)
        
        # 名前が一致するファイルがあれば、mimeTypeに関係なく返す
        if files_by_name:
            return files_by_name[0]
        elif files:
            return files[0]  # 最初に見つかったファイルを返す
        else:
            return None
            
    except Exception as e:
        st.error(f"ファイル検索エラー: {e}")
        st.error(f"エラー詳細: {str(e)}")
        return None


def download_csv_from_drive(file_id, drive_service):
    """Google DriveからCSVファイルをダウンロード"""
    config = load_config()
    
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        file_io.seek(0)
        
        # 設定から複数のエンコードを試す
        encodings = config["encodings"]
        
        for encoding in encodings:
            try:
                file_io.seek(0)
                df = pd.read_csv(file_io, encoding=encoding)
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                st.warning(f"エンコード '{encoding}' でエラー: {e}")
                continue
        
        # すべてのエンコードで失敗した場合、エラーを無視して読み込み
        try:
            file_io.seek(0)
            df = pd.read_csv(file_io, encoding='utf-8', errors='ignore')
            st.warning("一部の文字が正しく読み込めない可能性があります")
            return df
        except Exception as e:
            st.error(f"ファイルの読み込みに失敗しました: {e}")
            return None
        
    except Exception as e:
        st.error(f"ファイルダウンロードエラー: {e}")
        return None


def create_summary_table_and_chart(df, selected_column):
    """選択された列でデータを集計し、表とグラフを作成（収入と支出を分けて集計）"""
    if df is None or df.empty:
        st.warning("データがありません")
        return
    
    # 金額列が存在するかチェック
    if '金額' not in df.columns:
        st.error("金額列がデータに存在しません")
        return
    
    # 収入/支出列が存在するかチェック
    if '収入/支出' not in df.columns:
        st.error("収入/支出列がデータに存在しません")
        return
    
    try:
        # 収入と支出でデータを分ける
        income_df = df[df['収入/支出'] == '収入']
        expense_df = df[df['収入/支出'] == '支出']
        
        # 収入の集計
        if not income_df.empty:
            income_summary = (income_df.groupby(selected_column)['金額']
                              .sum().reset_index())
            income_summary = income_summary.sort_values('金額', ascending=False)
            
            st.subheader(f"収入 - {selected_column}別集計")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**収入集計表**")
                st.dataframe(income_summary, use_container_width=True)
                
                # 収入統計情報
                st.write("**収入統計**")
                st.metric("収入総計", f"¥{income_summary['金額'].sum():,}")
                st.metric("収入項目数", len(income_summary))
                if len(income_summary) > 0:
                    st.metric("収入平均", f"¥{income_summary['金額'].mean():,.0f}")
            
            with col2:
                # 収入棒グラフ
                fig_income_bar = px.bar(
                    income_summary,
                    x=selected_column,
                    y='金額',
                    title=f"収入 - {selected_column}別金額",
                    labels={'金額': '金額 (円)'},
                    color_discrete_sequence=['#2E8B57']  # 緑色
                )
                fig_income_bar.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_income_bar, use_container_width=True)
                
                # 収入円グラフ
                if len(income_summary) > 1:
                    fig_income_pie = px.pie(
                        income_summary,
                        values='金額',
                        names=selected_column,
                        title=f"収入 - {selected_column}別割合",
                        color_discrete_sequence=px.colors.sequential.Greens_r
                    )
                    st.plotly_chart(fig_income_pie, use_container_width=True)
        else:
            st.info("収入データがありません")
        
        st.markdown("---")
        
        # 支出の集計
        if not expense_df.empty:
            expense_summary = (expense_df.groupby(selected_column)['金額']
                               .sum().reset_index())
            expense_summary = (expense_summary.sort_values('金額',
                                                           ascending=False))
            
            st.subheader(f"支出 - {selected_column}別集計")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**支出集計表**")
                st.dataframe(expense_summary, use_container_width=True)
                
                # 支出統計情報
                st.write("**支出統計**")
                st.metric("支出総計", f"¥{expense_summary['金額'].sum():,}")
                st.metric("支出項目数", len(expense_summary))
                if len(expense_summary) > 0:
                    st.metric("支出平均", f"¥{expense_summary['金額'].mean():,.0f}")
            
            with col2:
                # 支出棒グラフ
                fig_expense_bar = px.bar(
                    expense_summary,
                    x=selected_column,
                    y='金額',
                    title=f"支出 - {selected_column}別金額",
                    labels={'金額': '金額 (円)'},
                    color_discrete_sequence=['#DC143C']  # 赤色
                )
                fig_expense_bar.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_expense_bar, use_container_width=True)
                
                # 支出円グラフ
                if len(expense_summary) > 1:
                    fig_expense_pie = px.pie(
                        expense_summary,
                        values='金額',
                        names=selected_column,
                        title=f"支出 - {selected_column}別割合",
                        color_discrete_sequence=px.colors.sequential.Reds_r
                    )
                    st.plotly_chart(fig_expense_pie, use_container_width=True)
        else:
            st.info("支出データがありません")
        
        st.markdown("---")
        
        # 総合統計情報
        st.subheader("総合統計")
        col1, col2, col3, col4 = st.columns(4)
        
        total_income = (income_summary['金額'].sum() 
                       if not income_df.empty else 0)
        total_expense = (expense_summary['金額'].sum() 
                        if not expense_df.empty else 0)
        net_amount = total_income - total_expense
        
        with col1:
            st.metric("総収入", f"¥{total_income:,}")
        with col2:
            st.metric("総支出", f"¥{total_expense:,}")
        with col3:
            delta_text = (f"¥{net_amount:,}" if net_amount >= 0 
                         else f"-¥{abs(net_amount):,}")
            st.metric("収支差額", f"¥{net_amount:,}", delta=delta_text)
        with col4:
            savings_rate = ((net_amount / total_income * 100) 
                           if total_income > 0 else 0)
            st.metric("貯蓄率", f"{savings_rate:.1f}%")
            
    except Exception as e:
        st.error(f"集計エラー: {e}")
        st.error(f"エラー詳細: {str(e)}")


def main():
    config = load_config()
    
    st.set_page_config(
        page_title=config["app_title"],
        layout=config["layout"]
    )
    
    st.title(config['app_title'])
    st.markdown("---")
    
    # サイドバーで年月選択
    st.sidebar.header("設定")
    
    # 年の選択
    current_year = datetime.now().year
    years = list(range(current_year - 5, current_year + 2))
    selected_year = st.sidebar.selectbox("年を選択", years, index=5)
    
    # 月の選択
    months = list(range(1, 13))
    selected_month = st.sidebar.selectbox(
        "月を選択",
        months,
        format_func=lambda x: f"{x}月 ({calendar.month_name[x]})"
    )
    
    # 年月を6桁の文字列に変換
    year_month = f"{selected_year}{selected_month:02d}"
    
    # データ読み込みボタン
    if st.sidebar.button("データを読み込む", type="primary"):
        st.session_state.load_data = True
        st.session_state.year_month = year_month
    
    # メインエリア
    if hasattr(st.session_state, 'load_data') and st.session_state.load_data:
        st.subheader(f"{selected_year}年{selected_month}月のデータ")
        
        with st.spinner("Google Driveからデータを読み込み中..."):
            drive_service = get_drive_service()
            
            if drive_service:
                # CSVファイルを検索
                file_info = search_csv_file_in_drive(
                    st.session_state.year_month, drive_service
                )
                
                if file_info:
                    # CSVファイルをダウンロード
                    df = download_csv_from_drive(
                        file_info['id'], drive_service
                    )
                    
                    if df is not None:
                        st.session_state.df = df
                        
                        # 列選択
                        st.markdown("---")
                        st.subheader("集計設定")
                        
                        # 利用可能な列を表示
                        available_columns = [
                            col for col in df.columns if col != '金額'
                        ]
                        
                        if available_columns:
                            selected_column = st.selectbox(
                                "集計する列を選択してください",
                                available_columns,
                                help="選択した列の値ごとに金額を合計します"
                            )
                            
                            if st.button("集計実行", type="primary"):
                                create_summary_table_and_chart(
                                    df, selected_column
                                )
                        else:
                            st.warning("集計可能な列がありません")
                    
                else:
                    filename = f"record{st.session_state.year_month}.csv"
                    error_msg = f"ファイル '{filename}' が見つかりませんでした"
                    st.error(error_msg)
            else:
                st.error("Google Drive APIに接続できませんでした")


if __name__ == "__main__":
    main()
