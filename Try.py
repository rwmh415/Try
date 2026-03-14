import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 核心邏輯：自定義 ADX 計算函數 (免安裝外部套件) ---
def calculate_adx(df, length=14):
    df = df.copy()
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # 計算 TR (True Range)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 計算方向變動 (DM)
    up_move = high.diff()
    down_move = low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), abs(down_move), 0)
    
    # 使用平滑移動平均計算 ATR, +DI, -DI
    atr = tr.rolling(window=length).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(window=length).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=length).mean() / atr)
    
    # 計算 DX 與 ADX
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(window=length).mean()
    return adx

# --- 網頁配置 ---
st.set_page_config(page_title="日內交易決策系統", layout="wide")
st.title("📊 日內交易決策系統 (方案 B: 輕量穩定版)")

# --- 側邊欄設定 ---
st.sidebar.header("設定參數")
ticker = st.sidebar.text_input("輸入股票/期貨代碼", "NQ=F")
va_threshold = st.sidebar.number_input("VA 寬度分水嶺 (%)", value=0.35, step=0.01)
adx_threshold = st.sidebar.number_input("ADX 強弱分水嶺", value=25.0, step=1.0)

if st.sidebar.button("開始分析"):
    with st.spinner(f"正在抓取 {ticker} 實時數據..."):
        try:
            # 抓取 5 天內的 15 分鐘線 (yfinance 限制 15m 資料最多只能抓近 60 天)
            df = yf.download(ticker, period="5d", interval="15m")
            
            if df.empty:
                st.error("找不到數據，請確認代碼（例如美股 AAPL, 指數期貨 NQ=F）")
            else:
                # 執行自定義 ADX 計算
                df['ADX_14'] = calculate_adx(df)
                
                # 取得最新一筆數據
                latest = df.iloc[-1]
                # 處理 yfinance 可能產生的 MultiIndex 格式
                price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
                adx_val = float(latest['ADX_14'].iloc[0]) if isinstance(latest['ADX_14'], pd.Series) else float(latest['ADX_14'])
                
                # 近似計算 VA 寬度 (當日高低差)
                today_df = df.loc[df.index.date == df.index[-1].date()]
                high_val = float(today_df['High'].max())
                low_val = float(today_df['Low'].min())
                va_width = ((high_val - low_val) / price) * 100

                # --- 儀表板展示 ---
                c1, c2, c3 = st.columns(3)
                c1.metric("目前價格", f"{price:,.2f}")
                c2.metric("VA 寬度 (估)", f"{va_width:.2f}%")
                c3.metric("ADX 動能", f"{adx_val:.2f}")

                st.divider()

                # --- 邏輯判斷 ---
                if va_width < va_threshold and adx_val < adx_threshold:
                    st.success("### ✅ 判定結果：高盤整環境 (震盪市)")
                    st.info("**決策：鎖定均值回歸劇本** (模型 2, 4, 7)")
                elif va_width >= va_threshold and adx_val >= adx_threshold:
                    st.warning("### ✅ 判定結果：趨勢擴張環境 (趨勢市)")
                    st.error("**決策：開啟順勢追擊劇本** (模型 3, 5, 14)")
                else:
                    st.info("### ✅ 判定結果：市況不明 (過渡期)")
                    st.write("目前指標分歧，建議觀望 09:30-10:00 交叉驗證期。")

                with st.expander("查看原始數據"):
                    st.write(df.tail(10))
        except Exception as e:
            st.error(f"分析失敗: {str(e)}")
