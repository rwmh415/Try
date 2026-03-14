import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 網頁設定 ---
st.set_page_config(page_title="日內交易決策系統", layout="wide")
st.title("📊 日內交易決策系統 (基於 VA 寬度與 ADX)")
st.markdown("此系統利用 Yahoo Finance 即時數據，分析指定標的的市況，並給出**均值回歸**或**順勢追擊**的劇本建議。")

# --- 側邊欄：參數設定 ---
st.sidebar.header("設定參數")
ticker = st.sidebar.text_input("輸入股票/期貨代碼 (例如: NQ=F, AAPL, NVDA)", "NQ=F")
va_threshold = st.sidebar.number_input("VA 寬度分水嶺 (%)", value=0.35, step=0.05)
adx_threshold = st.sidebar.number_input("ADX 強弱分水嶺", value=25.0, step=1.0)

# --- 核心邏輯 ---
if st.sidebar.button("開始分析"):
    with st.spinner(f"正在載入 {ticker} 的數據..."):
        try:
            # 獲取最近 5 天的 15 分鐘 K 線資料 (確保有足夠資料計算 ADX)
            df = yf.download(ticker, period="5d", interval="15m")
            
            if df.empty:
                st.error("無法獲取數據，請檢查股票代碼是否正確。")
            else:
                # 1. 計算 ADX (使用 pandas_ta)
                # 一般 ADX 週期設為 14
                df.ta.adx(length=14, append=True)
                
                # 取得最新一筆完整數據
                latest_data = df.iloc[-1]
                current_price = latest_data['Close'].iloc[0] if isinstance(latest_data['Close'], pd.Series) else latest_data['Close']
                current_adx = latest_data['ADX_14']
                
                # 2. 估算 VA 寬度 (Value Area Width)
                # 由於 Yahoo Finance 沒有直接提供 Tick 級別的成交量分佈 (Volume Profile)
                # 這裡我們使用當日最高價與最低價的區間，或是近 10 根 K 線的真實波幅 (ATR) 來「近似」價值區的寬度
                # 公式：VA 寬度 = (當日最高 - 當日最低) / 目前價格
                today_data = df.loc[df.index.date == df.index[-1].date()]
                if not today_data.empty:
                    val = today_data['Low'].min()
                    vah = today_data['High'].max()
                else:
                    val = df['Low'].iloc[-10:].min()
                    vah = df['High'].iloc[-10:].max()
                
                # 將 pd.Series 轉為純數值避免錯誤
                val = float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)
                vah = float(vah.iloc[0]) if isinstance(vah, pd.Series) else float(vah)
                current_price = float(current_price)
                
                va_width_pct = ((vah - val) / current_price) * 100

                # --- 介面展示 ---
                col1, col2, col3 = st.columns(3)
                col1.metric("目前價格", f"{current_price:.2f}")
                col2.metric("估算 VA 寬度", f"{va_width_pct:.2f}%", f"{va_width_pct - va_threshold:.2f}% (距分水嶺)")
                col3.metric("目前 ADX (動能)", f"{current_adx:.2f}")

                st.markdown("---")
                
                # --- 決策樹邏輯判定 ---
                st.subheader("💡 系統判定與劇本建議")
                
                if va_width_pct < va_threshold and current_adx < adx_threshold:
                    st.success("✅ 判定結果：**高盤整環境 (震盪市)**")
                    st.info("""
                    **執行決策：強制鎖定均值回歸劇本**
                    * **狀態分析：** 價值區窄小 (小於 0.35%)，且趨勢動能低迷，市場缺乏明確方向。
                    * **操作建議：** 採取高出低進策略。
                    * **適用模型：** 區間交易、均值回歸、盤整突破失守 (假突破反做)。
                    """)
                elif va_width_pct >= va_threshold and current_adx >= adx_threshold:
                    st.success("✅ 判定結果：**趨勢擴張環境 (趨勢市)**")
                    st.warning("""
                    **執行決策：開啟順勢追擊劇本**
                    * **狀態分析：** 價值區擴大 (大於 0.35%)，且 ADX 顯示趨勢強勁。
                    * **操作建議：** 不要猜頭摸底，順著突破方向追擊或等待回踩後順勢進場。
                    * **適用模型：** 順勢突破、趨勢回踩、趨勢波段。
                    """)
                else:
                    st.success("✅ 判定結果：**過渡期 / 複雜環境**")
                    st.markdown("""
                    **執行決策：建議觀望或縮小部位**
                    * **狀態分析：** VA 寬度與 ADX 指標出現分歧（例如：波動率大但無明確趨勢，或有趨勢但空間未打開）。
                    * **操作建議：** 等待 09:30-10:00 的早盤籌碼沉澱，直到指標方向一致。
                    """)
                    
                # 顯示原始數據供參考
                with st.expander("查看近期數據明細"):
                    st.dataframe(df[['Open', 'High', 'Low', 'Close', 'Volume', 'ADX_14']].tail(10))

        except Exception as e:
            st.error(f"發生錯誤: {e}")
