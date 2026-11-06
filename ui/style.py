"""Theme CSS and page header for the scanner app.
Palette: #FFFFFF, #E5E5E5, #C7C7C7, #525252, #2C2C2C, #E81D23
"""
import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
        /* Global Styles */
        .stApp {
            background-color: #FFFFFF;
            color: #2C2C2C;
        }

        /* Headings */
        h1, h2, h3, h4, h5, h6 {
            color: #2C2C2C !important;
            font-weight: 700 !important;
        }

        /* Dividers */
        hr {
            border: none !important;
            border-top: 1px solid #C7C7C7 !important;
            margin: 1rem 0 !important;
        }

        /* Primary Buttons (#E81D23) */
        button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background-color: #E81D23 !important;
            color: #FFFFFF !important;
            border: 1px solid #E81D23 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 5px rgba(232, 29, 35, 0.25) !important;
            transition: all 0.2s ease !important;
        }
        button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {
            background-color: #c7161b !important;
            border-color: #c7161b !important;
            box-shadow: 0 4px 10px rgba(232, 29, 35, 0.35) !important;
            transform: translateY(-1px);
        }

        /* Secondary / Default Buttons */
        button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {
            background-color: #E5E5E5 !important;
            color: #2C2C2C !important;
            border: 1px solid #C7C7C7 !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        button[kind="secondary"]:hover,
        button[data-testid="baseButton-secondary"]:hover {
            background-color: #C7C7C7 !important;
            border-color: #525252 !important;
            color: #2C2C2C !important;
        }

        /* Radio Group Styling */
        div[data-testid="stRadio"] > div {
            background-color: #E5E5E5;
            border: 1px solid #C7C7C7;
            border-radius: 8px;
            padding: 6px 14px;
            gap: 16px;
        }
        div[data-testid="stRadio"] label {
            color: #2C2C2C !important;
            font-weight: 500;
        }

        /* Checkbox & Selection */
        div[data-testid="stCheckbox"] {
            display: flex;
            justify-content: center;
            align-items: center;
            padding-top: 10px;
        }

        /* Card Containers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #C7C7C7 !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            margin-bottom: 8px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            transition: all 0.2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #525252 !important;
            box-shadow: 0 2px 8px rgba(44, 44, 44, 0.08) !important;
        }

        /* Badges & Text */
        .badge-category {
            background-color: #E5E5E5;
            color: #2C2C2C;
            border: 1px solid #C7C7C7;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.78rem;
            font-weight: 500;
            display: inline-block;
        }
        .badge-score {
            color: #E81D23;
            font-weight: 600;
            font-size: 0.8rem;
            margin-left: 6px;
        }
        .item-title {
            color: #2C2C2C;
            font-weight: 700;
            font-size: 0.98rem;
            line-height: 1.3;
        }
        .item-desc {
            color: #525252;
            font-size: 0.84rem;
            margin-top: 4px;
            line-height: 1.4;
        }

        /* File uploader & Camera container */
        div[data-testid="stFileUploader"],
        div[data-testid="stCameraInput"] {
            background-color: #FFFFFF;
            border: 1px dashed #C7C7C7;
            border-radius: 8px;
            padding: 8px;
        }

        /* Thumbnail image */
        .thumb-preview img {
            border: 1px solid #C7C7C7;
            border-radius: 6px;
        }

        /* Info / Alert Box Styling with Theme Palette */
        div[data-testid="stAlert"] {
            background-color: #E5E5E5 !important;
            border: 1px solid #C7C7C7 !important;
            border-left: 5px solid #525252 !important;
            color: #2C2C2C !important;
            border-radius: 8px !important;
        }
        div[data-testid="stAlert"] p {
            color: #2C2C2C !important;
            font-size: 0.92rem !important;
        }

        /* Custom Scrollbar for Containers */
        div[data-testid="stContainer"]::-webkit-scrollbar,
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        div[data-testid="stContainer"]::-webkit-scrollbar-track,
        ::-webkit-scrollbar-track {
            background: #E5E5E5;
            border-radius: 4px;
        }
        div[data-testid="stContainer"]::-webkit-scrollbar-thumb,
        ::-webkit-scrollbar-thumb {
            background: #C7C7C7;
            border-radius: 4px;
        }
        div[data-testid="stContainer"]::-webkit-scrollbar-thumb:hover,
        ::-webkit-scrollbar-thumb:hover {
            background: #E81D23;
        }

        /* Search Input */
        div[data-testid="stTextInput"] input {
            background-color: #FFFFFF !important;
            border: 1px solid #C7C7C7 !important;
            border-radius: 6px !important;
            color: #2C2C2C !important;
            font-size: 0.88rem !important;
            padding: 6px 12px !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #E81D23 !important;
            box-shadow: 0 0 0 1px #E81D23 !important;
        }

        /* Compact Row Container Tweaks */
        .compact-row-box [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 5px 8px !important;
            margin-bottom: 4px !important;
        }

        /* iPad & Mobile Touch Target Enhancements */
        /* Tabs for iPad & Mobile */
        div[data-testid="stTabs"] button[role="tab"] {
            padding: 12px 20px !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            color: #525252 !important;
            min-height: 48px !important;
            border-radius: 8px 8px 0 0 !important;
            touch-action: manipulation;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: #E81D23 !important;
            border-bottom: 3px solid #E81D23 !important;
            background-color: #FAFAFA !important;
        }

        /* Touch targets for Checkbox */
        div[data-testid="stCheckbox"] {
            min-width: 44px !important;
            min-height: 44px !important;
        }
        div[data-testid="stCheckbox"] label span[role="checkbox"] {
            width: 22px !important;
            height: 22px !important;
            border-radius: 6px !important;
            border: 2px solid #C7C7C7 !important;
        }
        div[data-testid="stCheckbox"] label span[role="checkbox"][aria-checked="true"] {
            background-color: #E81D23 !important;
            border-color: #E81D23 !important;
        }

        /* Action Buttons Touch Target */
        button[data-testid^="baseButton"] {
            min-height: 44px !important;
            font-size: 14px !important;
            touch-action: manipulation;
        }

        /* Delete Button */
        button[key^="del_"] {
            min-width: 40px !important;
            min-height: 40px !important;
        }

        /* Radio Group Touch Targets */
        div[data-testid="stRadio"] > div {
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        div[data-testid="stRadio"] label {
            min-height: 38px !important;
            padding: 6px 12px !important;
            touch-action: manipulation;
        }

        /* Progress Bar Color */
        .stProgress > div > div > div > div {
            background-color: #E81D23 !important;
        }

        /* ========================================================= */
        /* MOBILE FIX: PREVENT VERTICAL COLUMN BREAKING INSIDE CARDS */
        /* ========================================================= */
        /* Item Card Container (Nested inside checklist scroll container) */
        div[data-testid="stContainer"] div[data-testid="stContainer"] {
            padding: 6px 8px !important;
            margin-bottom: 6px !important;
            border-color: #C7C7C7 !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
        }

        /* Force the card's horizontal columns to remain strictly in 1 single horizontal row */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stHorizontalBlock"],
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stHorizontalBlock {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 6px !important;
            width: 100% !important;
        }

        /* Override min-width and flex on all 4 columns inside the item card */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"],
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn {
            min-width: 0 !important;
            margin-bottom: 0 !important;
        }

        /* Col 1: Checkbox */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(1),
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(1) {
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
            flex: 0 0 36px !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* Col 2: Image Thumbnail */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(2),
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(2) {
            width: 44px !important;
            min-width: 44px !important;
            max-width: 44px !important;
            flex: 0 0 44px !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* Col 3: Text content (title, category, score, desc) */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(3),
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(3) {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
            overflow: hidden !important;
        }

        /* Col 4: Delete button */
        div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(4),
        div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(4) {
            width: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            flex: 0 0 38px !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        /* Compact Delete Button in Card */
        div[data-testid="stContainer"] div[data-testid="stContainer"] button {
            min-width: 32px !important;
            width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 !important;
            font-size: 13px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-radius: 6px !important;
        }

        /* Top Action Buttons row: keep in 1 row on mobile */
        .top-action-bar .stHorizontalBlock,
        .top-action-bar [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
            width: 100% !important;
        }
        .top-action-bar .stColumn,
        .top-action-bar [data-testid="stColumn"],
        .top-action-bar [data-testid="column"],
        .top-action-bar [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 33.33% !important;
            min-width: 0 !important;
            width: 33.33% !important;
        }
        .top-action-bar button {
            padding: 8px 4px !important;
            font-size: 0.82rem !important;
        }

        /* Responsive adjustments specifically for Mobile Viewports (< 768px) */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.8rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            /* Item card padding on mobile */
            div[data-testid="stContainer"] div[data-testid="stContainer"] {
                padding: 5px 6px !important;
                margin-bottom: 4px !important;
            }
            /* Reinforce nowrap on mobile inside cards */
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stHorizontalBlock"],
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stHorizontalBlock {
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                gap: 4px !important;
            }
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"],
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn {
                min-width: 0 !important;
            }
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(1),
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(1) {
                width: 34px !important;
                min-width: 34px !important;
                max-width: 34px !important;
                flex: 0 0 34px !important;
            }
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(2),
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(2) {
                width: 42px !important;
                min-width: 42px !important;
                max-width: 42px !important;
                flex: 0 0 42px !important;
            }
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(3),
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(3) {
                flex: 1 1 auto !important;
                min-width: 0 !important;
                width: auto !important;
            }
            div[data-testid="stContainer"] div[data-testid="stContainer"] div[data-testid="stColumn"]:nth-of-type(4),
            div[data-testid="stContainer"] div[data-testid="stContainer"] .stColumn:nth-of-type(4) {
                width: 36px !important;
                min-width: 36px !important;
                max-width: 36px !important;
                flex: 0 0 36px !important;
            }
        }

        /* Processing Radar Animation & Modal Styling */
        @keyframes radar-sweep {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes pulse-ring {
            0% { box-shadow: 0 0 0 0 rgba(232, 29, 35, 0.45); }
            70% { box-shadow: 0 0 0 16px rgba(232, 29, 35, 0); }
            100% { box-shadow: 0 0 0 0 rgba(232, 29, 35, 0); }
        }
        .radar-scan-anim {
            width: 76px;
            height: 76px;
            border-radius: 50%;
            border: 3px solid #E81D23;
            background: radial-gradient(circle, rgba(232,29,35,0.12) 0%, rgba(229,229,229,0.4) 100%);
            margin: 0 auto;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse-ring 2s infinite;
        }
        .radar-beam {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: conic-gradient(from 0deg, rgba(232, 29, 35, 0.45) 0deg, transparent 65deg);
            animation: radar-sweep 2s linear infinite;
        }
        .radar-icon {
            font-size: 30px;
            z-index: 2;
        }

        /* Modal / Dialog Styling */
        div[role="dialog"] {
            border-radius: 12px !important;
            border: 2px solid #C7C7C7 !important;
            box-shadow: 0 8px 30px rgba(44, 44, 44, 0.2) !important;
        }
        div[role="dialog"] h2 {
            color: #2C2C2C !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            border-bottom: 1px solid #E5E5E5 !important;
            padding-bottom: 8px !important;
        }

        /* Custom Navigation Bar - Keep 3 tabs side by side on mobile & desktop */
        .custom-nav-bar {
            margin-bottom: 14px;
        }
        div[data-testid="stHorizontalBlock"]:has(button[key="nav_btn_scan"]) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 8px !important;
            width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(button[key="nav_btn_scan"]) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has(button[key="nav_btn_scan"]) > .stColumn {
            flex: 1 1 33.33% !important;
            min-width: 0 !important;
            width: 33.33% !important;
            max-width: 33.33% !important;
        }
        .custom-nav-bar button,
        button[key="nav_btn_scan"],
        button[key="nav_btn_check"],
        button[key="nav_btn_tray"] {
            height: 48px !important;
            min-height: 48px !important;
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            touch-action: manipulation;
            white-space: nowrap !important;
        }
        button[key="nav_btn_scan"][kind="primary"],
        button[key="nav_btn_check"][kind="primary"],
        button[key="nav_btn_tray"][kind="primary"] {
            background-color: #E81D23 !important;
            color: #FFFFFF !important;
            border: 2px solid #E81D23 !important;
            box-shadow: 0 2px 8px rgba(232, 29, 35, 0.25) !important;
        }
        button[key="nav_btn_scan"][kind="secondary"],
        button[key="nav_btn_check"][kind="secondary"],
        button[key="nav_btn_tray"][kind="secondary"] {
            background-color: #E5E5E5 !important;
            color: #525252 !important;
            border: 1px solid #C7C7C7 !important;
        }
        button[key="nav_btn_scan"][kind="secondary"]:hover,
        button[key="nav_btn_check"][kind="secondary"]:hover,
        button[key="nav_btn_tray"][kind="secondary"]:hover {
            background-color: #FFFFFF !important;
            color: #2C2C2C !important;
            border-color: #525252 !important;
        }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; background: #FFFFFF; border-bottom: 2px solid #C7C7C7; padding-bottom: 12px; margin-bottom: 15px; gap: 10px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background-color: #E81D23; color: #FFFFFF; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-weight: bold; box-shadow: 0 2px 6px rgba(232, 29, 35, 0.25);">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            </div>
            <div>
                <h1 style="margin: 0; color: #2C2C2C; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">ระบบเช็คลิสต์เครื่องมือ (Multi-Object)</h1>
                <p style="margin: 2px 0 0 0; color: #525252; font-size: 12px;">SIFT Feature Matching & Real-time Inspection</p>
            </div>
        </div>
        <div style="display: flex; gap: 6px; align-items: center;">
            <span style="background-color: #E5E5E5; color: #2C2C2C; border: 1px solid #C7C7C7; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px;">iPad/Mobile Ready</span>
            <span style="background-color: #E81D23; color: #FFFFFF; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px;">READY</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
