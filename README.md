<div align="center">
  <h1>📈 Binance Futures Trading Bot with AI Mode 🤖</h1>
  <p>
    <strong>🇮🇩 Bot Telegram untuk trading otomatis di Binance Futures dengan Mode AI konseptual (integrasi Gemini opsional).</strong><br>
    <strong>🇬🇧 Telegram Bot for automated trading on Binance Futures with a conceptual AI Mode (optional Gemini integration).</strong>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python" alt="Python 3.8+"/>
    <img src="https://img.shields.io/badge/Telegram%20Bot-Active-brightgreen?style=for-the-badge&logo=telegram" alt="Telegram Bot"/>
    <img src="https://img.shields.io/badge/Binance%20Futures-Supported-yellow?style=for-the-badge&logo=binance" alt="Binance Futures"/>
  </p>
</div>

---

🚨 **PERINGATAN PENTING / IMPORTANT WARNING** 🚨

🇮🇩 **TRADING CRYPTOCURRENCY FUTURES MEMILIKI RISIKO SANGAT TINGGI. ANDA BISA KEHILANGAN SELURUH MODAL ANDA. GUNAKAN BOT INI DENGAN RISIKO ANDA SENDIRI. TIDAK ADA JAMINAN PROFIT. LAKUKAN RISET ANDA SENDIRI (DYOR) DAN UJI COBA SECARA EKSTENSIF DALAM MODE SIMULASI SEBELUM MENGGUNAKAN DANA RIIL.**

🇬🇧 **CRYPTOCURRENCY FUTURES TRADING CARRIES A VERY HIGH LEVEL OF RISK. YOU CAN LOSE ALL YOUR CAPITAL. USE THIS BOT AT YOUR OWN RISK. THERE IS NO GUARANTEE OF PROFIT. DO YOUR OWN RESEARCH (DYOR) AND TEST EXTENSIVELY IN SIMULATION MODE BEFORE USING REAL FUNDS.**

---

## 📜 Daftar Isi / Table of Contents

🇮🇩
1.  [✨ Fitur Utama](#fitur-utama-id)
2.  [🛠️ Persiapan yang Dibutuhkan](#persiapan-yang-dibutuhkan-id)
3.  [⚙️ Instalasi & Konfigurasi](#instalasi--konfigurasi-id)
4.  [🚀 Cara Menjalankan Bot](#cara-menjalankan-bot-id)
5.  [📲 Perintah Telegram](#perintah-telegram-id)
6.  [🧠 Mode AI (Konseptual dengan Gemini)](#mode-ai-konseptual-dengan-gemini-id)
7.  [⚠️ Risiko Penggunaan](#risiko-penggunaan-id)
8.  [📄 Disclaimer](#disclaimer-id)
9.  [🏆 Kredit](#kredit-id)
10. [📝 Lisensi](#lisensi-id)

🇬🇧
1.  [✨ Key Features](#key-features-en)
2.  [🛠️ Prerequisites](#prerequisites-en)
3.  [⚙️ Installation & Configuration](#installation--configuration-en)
4.  [🚀 How to Run the Bot](#how-to-run-the-bot-en)
5.  [📲 Telegram Commands](#telegram-commands-en)
6.  [🧠 AI Mode (Conceptual with Gemini)](#ai-mode-conceptual-with-gemini-en)
7.  [⚠️ Risks of Use](#risks-of-use-en)
8.  [📄 Disclaimer](#disclaimer-en)
9.  [🏆 Credits](#credits-en)
10. [📝 License](#license-en)

---

## <a id="fitur-utama-id"></a>✨ Fitur Utama (🇮🇩)

*   **🤖 Trading Otomatis**: Melakukan entry dan exit posisi berdasarkan sinyal dari Analisis Teknis (TA).
*   **🛡️ Manajemen Posisi**:
    *   Otomatis mengatur Take Profit (TP) dan Stop Loss (SL).
    *   Mendukung Hedge Mode di Binance Futures.
*   **🕹️ Mode Trading**:
    *   **Manual/Rule-Based**: Pilih mode (Aman, Standar, Agresif) dengan parameter yang telah ditentukan.
    *   **Mode AI (Konseptual)**:
        *   Bot mencoba mengoptimalkan `trading_mode` & parameter `INDICATOR_SETTINGS`.
        *   **Integrasi Gemini AI (Opsional & Eksperimental)**: Dapat meminta rekomendasi dari Gemini AI jika dikonfigurasi. Jika tidak, menggunakan logika rule-based.
*   **🔎 Seleksi Pair Trading**:
    *   **Statis**: Trading pada daftar pair yang ditentukan.
    *   **Dinamis**: Memindai watchlist, memilih pair likuid & bersinyal kuat.
*   **📊 Indikator Teknis**: Menggunakan RSI, EMA, dan Bollinger Bands. Parameter dapat disesuaikan manual atau oleh AI.
*   **⚖️ Manajemen Risiko**:
    *   Ukuran posisi (persentase balance / jumlah USDT tetap).
    *   Target profit & batas kerugian harian.
    *   Maksimum trade harian.
*   **🔔 Notifikasi Telegram**: Update real-time status bot, trade, perubahan AI, statistik, dll.
*   **📱 Kontrol via Telegram**: Kendali penuh melalui perintah Telegram untuk admin.

## <a id="key-features-en"></a>✨ Key Features (🇬🇧)

*   **🤖 Automated Trading**: Executes entries and exits based on Technical Analysis (TA) signals.
*   **🛡️ Position Management**:
    *   Automatically sets Take Profit (TP) and Stop Loss (SL).
    *   Supports Hedge Mode on Binance Futures.
*   **🕹️ Trading Modes**:
    *   **Manual/Rule-Based**: Choose predefined modes (Safe, Standard, Aggressive) with distinct parameters.
    *   **AI Mode (Conceptual)**:
        *   The bot attempts to optimize `trading_mode` & `INDICATOR_SETTINGS` parameters.
        *   **Gemini AI Integration (Optional & Experimental)**: Can request recommendations from Gemini AI if configured. Otherwise, uses rule-based logic.
*   **🔎 Trading Pair Selection**:
    *   **Static**: Trades on a user-defined list of pairs.
    *   **Dynamic**: Periodically scans a watchlist, selecting liquid pairs with strong TA signals.
*   **📊 Technical Indicators**: Utilizes RSI, EMA, and Bollinger Bands. Parameters are adjustable manually or by AI.
*   **⚖️ Risk Management**:
    *   Position sizing (percentage of balance / fixed USDT amount).
    *   Daily profit target & loss limit.
    *   Maximum daily trades.
*   **🔔 Telegram Notifications**: Real-time updates on bot status, trades, AI changes, stats, etc.
*   **📱 Control via Telegram**: Full control through Telegram commands for authorized admins.

---

## <a id="persiapan-yang-dibutuhkan-id"></a>🛠️ Persiapan yang Dibutuhkan (🇮🇩)

1.  **🪙 Akun Binance**: Terverifikasi, saldo USDT (untuk trading riil), Fitur Futures aktif.
2.  **🔑 API Key Binance**:
    *   Izin: `Enable Reading`, `Enable Futures`.
    *   **JANGAN** aktifkan `Enable Withdrawals`.
    *   Whitelist IP server jika perlu.
3.  **🧠 API Key Google Gemini (Opsional)**: Dari [Google AI Studio](https://aistudio.google.com/) / Vertex AI.
4.  **🖥️ Server/Komputer**: VPS, Raspberry Pi, atau PC lokal (berjalan 24/7) dengan Python 3.8+.
5.  **🤖 Token Bot Telegram**: Dari @BotFather.
6.  **🆔 ID User Telegram Admin**: ID numerik akun Telegram Anda (dari @userinfobot).

## <a id="prerequisites-en"></a>🛠️ Prerequisites (🇬🇧)

1.  **🪙 Binance Account**: Verified, USDT balance (for real trading), Futures feature activated.
2.  **🔑 Binance API Key**:
    *   Permissions: `Enable Reading`, `Enable Futures`.
    *   **NEVER** enable `Enable Withdrawals`.
    *   Whitelist server IP if necessary.
3.  **🧠 Google Gemini API Key (Optional)**: From [Google AI Studio](https://aistudio.google.com/) / Vertex AI.
4.  **🖥️ Server/Computer**: VPS, Raspberry Pi, or local PC (running 24/7) with Python 3.8+.
5.  **🤖 Telegram Bot Token**: From @BotFather.
6.  **🆔 Admin Telegram User ID**: Your numeric Telegram account ID (from @userinfobot).

---

## <a id="instalasi--konfigurasi-id"></a>⚙️ Instalasi & Konfigurasi (🇮🇩)

1.  **📥 Clone Repository (Jika ada)** atau salin file kode `.py`.
2.  **📦 Install Pustaka Python**:
    ```bash
    pip install python-telegram-bot pandas numpy pandas-ta requests google-generativeai python-dotenv
    ```
3.  **📄 Buat File `.env`**: Di direktori yang sama dengan script, isi dengan kredensial Anda:
    ```env
    GEMINI_API_KEY_ENV="API_KEY_GEMINI_ANDA_JIKA_ADA"
    TELEGRAM_BOT_TOKEN_ENV="TOKEN_BOT_TELEGRAM_ANDA"
    BINANCE_API_KEY_ENV="KUNCI_API_BINANCE_ANDA"
    BINANCE_API_SECRET_ENV="RAHASIA_API_BINANCE_ANDA"
    ADMIN_USER_IDS_ENV="ID_ADMIN_1,ID_ADMIN_2" # Pisahkan dengan koma jika >1
    ```
4.  **🔧 Konfigurasi Internal Bot (dalam script Python)**:
    *   Sesuaikan `CONFIG` & `AI_MODE_CONFIG`.
    *   `CONFIG["use_real_trading"]`: `True` (riil) / `False` (simulasi).
    *   `CONFIG["ai_mode_active"]`: `True` untuk AI aktif saat start.
    *   `AI_MODE_CONFIG["use_gemini_for_analysis"]`: `True` untuk mencoba Gemini (perlu API Key valid).

## <a id="installation--configuration-en"></a>⚙️ Installation & Configuration (🇬🇧)

1.  **📥 Clone Repository (If applicable)** or copy the `.py` code file.
2.  **📦 Install Python Libraries**:
    ```bash
    pip install python-telegram-bot pandas numpy pandas-ta requests google-generativeai python-dotenv
    ```
3.  **📄 Create `.env` File**: In the same directory as the script, fill it with your credentials:
    ```env
    GEMINI_API_KEY_ENV="YOUR_GEMINI_API_KEY_IF_ANY"
    TELEGRAM_BOT_TOKEN_ENV="YOUR_TELEGRAM_BOT_TOKEN"
    BINANCE_API_KEY_ENV="YOUR_BINANCE_API_KEY"
    BINANCE_API_SECRET_ENV="YOUR_BINANCE_API_SECRET"
    ADMIN_USER_IDS_ENV="ADMIN_ID_1,ADMIN_ID_2" # Comma-separate if >1
    ```
4.  **🔧 Internal Bot Configuration (in the Python script)**:
    *   Adjust `CONFIG` & `AI_MODE_CONFIG`.
    *   `CONFIG["use_real_trading"]`: `True` (real) / `False` (simulation).
    *   `CONFIG["ai_mode_active"]`: `True` for AI active on start.
    *   `AI_MODE_CONFIG["use_gemini_for_analysis"]`: `True` to try Gemini (requires valid API Key).

---

## <a id="cara-menjalankan-bot-id"></a>🚀 Cara Menjalankan Bot (🇮🇩)

1.  Buka terminal/command prompt.
2.  Navigasi ke direktori script.
3.  Jalankan: `python FutureAI.py`
4.  Bot akan mulai. Interaksi via Telegram dengan `/start`.

## <a id="how-to-run-the-bot-en"></a>🚀 How to Run the Bot (🇬🇧)

1.  Open terminal/command prompt.
2.  Navigate to the script directory.
3.  Run: `python FutureAI.py`
4.  The bot will start. Interact via Telegram with `/start`.

---

## <a id="perintah-telegram-id"></a>📲 Perintah Telegram (🇮🇩)

(Hanya untuk admin)

*   **ℹ️ Info**: `/start`, `/help`, `/status`, `/config`, `/trades`, `/stats`, `/balance`, `/positions`, `/indicators <SIMBOL>`, `/scannedpairs`
*   **💸 Trading**: `/starttrade`, `/stoptrade`, `/closeall` (Hati-hati!)
*   **⚙️ Pengaturan**: `/set <param> <val>`, `/setmode <mode>`, `/setleverage <X>`, `/setprofit <target%> <limit%>`, `/addpair <SIMBOL>`, `/removepair <SIMBOL>`
*   **🌐 Dinamis**: `/toggledynamic`, `/watchlist <cmd> [SIMBOL_CSV]`
*   **🧠 AI Mode**:
    *   `/toggleai`: Aktifkan/Nonaktifkan AI Mode.
    *   `/togglegemini`: Aktifkan/Nonaktifkan penggunaan Gemini (jika AI Mode aktif).
    *   `/runaiopt`: Paksa siklus optimasi AI sekarang.
*   **🔩 Sistem**: `/enablereal`, `/disablereal`, `/testapi`

## <a id="telegram-commands-en"></a>📲 Telegram Commands (🇬🇧)

(For admins only)

*   **ℹ️ Info**: `/start`, `/help`, `/status`, `/config`, `/trades`, `/stats`, `/balance`, `/positions`, `/indicators <SYMBOL>`, `/scannedpairs`
*   **💸 Trading**: `/starttrade`, `/stoptrade`, `/closeall` (Use with caution!)
*   **⚙️ Settings**: `/set <param> <val>`, `/setmode <mode>`, `/setleverage <X>`, `/setprofit <target%> <limit%>`, `/addpair <SYMBOL>`, `/removepair <SYMBOL>`
*   **🌐 Dynamic**: `/toggledynamic`, `/watchlist <cmd> [SYMBOL_CSV]`
*   **🧠 AI Mode**:
    *   `/toggleai`: Enable/Disable AI Mode.
    *   `/togglegemini`: Enable/Disable Gemini usage (if AI Mode is ON).
    *   `/runaiopt`: Force AI optimizer cycle now.
*   **🔩 System**: `/enablereal`, `/disablereal`, `/testapi`

---

## <a id="mode-ai-konseptual-dengan-gemini-id"></a>🧠 Mode AI (Konseptual dengan Gemini) (🇮🇩)

Fitur ini **eksperimental**.

*   **Cara Kerja**: Jika AI Mode aktif, bot secara periodik menganalisis pasar (volatilitas ATR BTC). Jika penggunaan Gemini aktif & API Key valid, bot meminta rekomendasi mode trading & parameter indikator dari Gemini. Jika tidak, menggunakan logika rule-based. Pengaturan diterapkan & admin dinotifikasi.
*   **Prompt Gemini**: Kualitas rekomendasi Gemini bergantung pada kualitas prompt. Prompt saat ini adalah dasar & mungkin perlu perbaikan.
*   **Biaya & Latency**: Panggilan API Gemini berbayar & memiliki latency.

## <a id="ai-mode-conceptual-with-gemini-en"></a>🧠 AI Mode (Conceptual with Gemini) (🇬🇧)

This feature is **experimental**.

*   **How it Works**: If AI Mode is active, the bot periodically analyzes the market (BTC ATR volatility). If Gemini usage is active & API Key valid, it requests trading mode & indicator parameter recommendations from Gemini. Otherwise, it uses rule-based logic. Settings are applied & admin notified.
*   **Gemini Prompts**: Gemini's recommendation quality depends heavily on prompt quality. Current prompts are basic & may need refinement.
*   **Cost & Latency**: Gemini API calls incur costs & have latency.

---

## <a id="risiko-penggunaan-id"></a>⚠️ Risiko Penggunaan (🇮🇩)

*   **📉 Kerugian Finansial**: Pasar kripto sangat volatil. Futures memperbesar risiko.
*   **🐛 Bug Perangkat Lunak**: Dapat menyebabkan perilaku tak terduga.
*   **🔗 Masalah API Exchange**: Gangguan API Binance dapat mempengaruhi bot.
*   **🌐 Koneksi Internet**: Koneksi tidak stabil dapat mengganggu operasi.
*   **🤖 Keputusan AI Tidak Optimal**: AI (termasuk Gemini) tidak menjamin keputusan yang selalu menguntungkan.
*   **🔒 Keamanan API Key**: Kebocoran API Key dapat membahayakan akun Anda.

## <a id="risks-of-use-en"></a>⚠️ Risks of Use (🇬🇧)

*   **📉 Financial Loss**: Crypto markets are highly volatile. Futures amplify risks.
*   **🐛 Software Bugs**: May cause unexpected behavior.
*   **🔗 Exchange API Issues**: Binance API disruptions can affect the bot.
*   **🌐 Internet Connection**: Unstable connection can disrupt operations.
*   **🤖 Suboptimal AI Decisions**: AI (including Gemini) doesn't guarantee profitable decisions.
*   **🔒 API Key Security**: Leaked API Keys can compromise your account.

---

## <a id="disclaimer-id"></a>📄 Disclaimer (🇮🇩)

Perangkat lunak ini disediakan "SEBAGAIMANA ADANYA", tanpa jaminan apapun. Penulis atau pemegang hak cipta tidak bertanggung jawab atas klaim, kerusakan, atau kewajiban lainnya yang timbul dari penggunaan perangkat lunak ini. Gunakan dengan risiko Anda sendiri.

## <a id="disclaimer-en"></a>📄 Disclaimer (🇬🇧)

This software is provided "AS IS", without warranty of any kind. The authors or copyright holders shall not be liable for any claim, damages, or other liability arising from the use of this software. Use at your own risk.

---

## <a id="kredit-id"></a>🏆 Kredit (🇮🇩)

*   **Pengembangan Awal & Modifikasi**: Kode ini adalah hasil pengembangan dan modifikasi dari berbagai sumber dan kontribusi.
*   **Untuk diskusi terkait implementasi AI dan fitur bot ini, hubungi**: Telegram [@JoestarMojo](https://t.me/JoestarMojo)

## <a id="credits-en"></a>🏆 Credits (🇬🇧)

*   **Initial Development & Modifications**: This code is the result of development and modifications from various sources and contributions.
*   **For discussions regarding AI implementation and features of this bot, contact**: Telegram [@JoestarMojo](https://t.me/JoestarMojo)

---

## <a id="lisensi-id"></a>📝 Lisensi (🇮🇩)

Proyek ini dapat menggunakan lisensi open source seperti MIT License jika dibagikan.

## <a id="license-en"></a>📝 License (🇬🇧)

This project may use an open-source license such as the MIT License if shared.

*(Contoh Lisensi MIT / Example MIT License)*
